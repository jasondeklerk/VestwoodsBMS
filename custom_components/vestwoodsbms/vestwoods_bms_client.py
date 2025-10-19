#hacs integration
import asyncio
import logging
import struct
import time
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import mqtt
import json

_LOGGER = logging.getLogger(__name__)

# Vestwoods BMS BLE UUIDs (Nordic UART Service)
SERVICE_UUID = "6e400000-b5a3-f393-e0a9-e50e24dcca9e"
# SWAPPED ROLES based on characteristic discovery:
TX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # Write to this characteristic (was RX)
RX_CHAR_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Read/Notify from this characteristic (was TX)

# Polling command for Vestwoods BMS (from batVestwoods.cpp)
POLL_COMMAND = bytearray([0x7a, 0x00, 0x05, 0x00, 0x00, 0x01, 0x0c, 0xe5, 0xa7])

def calc_crc(data: bytearray) -> int:
    """Calculates the CRC16 for the given data, matching the C++ implementation."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001  # Equivalent to 40961 in decimal
            else:
                crc >>= 1
    return crc & 0xFFFF

def parse_response(data: bytearray) -> dict:
    """Parses the BMS response data (command 0x0001)"""
    if not data or len(data) < 8:
        _LOGGER.warning("Response too short to be valid.")
        return {}

    # Validate start and end sentinels
    if data[0] != 0x7a or data[-1] != 0xa7:
        _LOGGER.warning(f"Invalid sentinels: Start={hex(data[0])}, End={hex(data[-1])}")
        return {}

    # Validate length
    payload_len = data[2]
    if len(data) != payload_len + 4:
        _LOGGER.warning(f"Invalid length: Expected {payload_len + 4}, Got {len(data)}")
        return {}

    # Validate CRC
    data_for_crc = data[1 : len(data) - 3] # Exclude start, CRC (2 bytes), End (1 byte)
    calculated_crc = calc_crc(data_for_crc)

    msg_crc_bytes = data[len(data) - 3 : len(data) - 1]
    msg_crc = struct.unpack('>H', msg_crc_bytes)[0]

    if msg_crc != calculated_crc:
        _LOGGER.warning(f"CRC mismatch: Message CRC={hex(msg_crc)}, Calculated CRC={hex(calculated_crc)}")
        return {}

    # Parse payload (starting from byte 4: after 0x7a, unknown, length, unknown)
    offset = 4 
    command_received = struct.unpack('>H', data[4:6])[0]
    if command_received != 0x0001:
        _LOGGER.warning(f"Unexpected command received: {hex(command_received)}")
        return {}
    
    offset = 6 # Start of actual data fields after command
    
    result = {}

    # 0 - onlineStatus
    result['onlineStatus'] = data[offset]
    offset += 1

    # 1 - batteriesSeriesNumber
    num_cells = data[offset]
    result['batteriesSeriesNumber'] = num_cells
    offset += 1

    result['cellVoltages'] = []
    for j in range(num_cells):
        # 2, 3 - cellVoltage (mV)
        cell_voltage_raw = struct.unpack('>H', data[offset : offset + 2])[0] & 0x7fff
        result['cellVoltages'].append(round(cell_voltage_raw / 1000.0, 3))
        offset += 2
    
    # 4 - maxCellNumber
    result['maxCellNumber'] = data[offset]
    offset += 1

    # 5,6 - maxCellVoltage
    result['maxCellVoltage'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 1000.0, 3)
    offset += 2

    # 7 - minCellNumber
    result['minCellNumber'] = data[offset]
    offset += 1

    # 8,9 - minCellVoltage
    result['minCellVoltage'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 1000.0, 3)
    offset += 2

    # 10,11 - totalCurrent ( x / 100 - 300 )
    total_current_raw = struct.unpack('>H', data[offset : offset + 2])[0]
    result['totalCurrent'] = round((total_current_raw / 100.0) - 300.0, 2)
    offset += 2

    # 12, 13 - soc (x / 100)
    result['soc'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 14, 15 - soh (x / 100)
    result['soh'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 16, 17 - actualCapacity (x / 100)
    result['actualCapacity'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 18, 19 - surplusCapacity (x / 100)
    result['surplusCapacity'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 20, 21 - nominalCapacity (x / 100)
    result['nominalCapacity'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 22 - batteriesTemperatureNumber
    temp_count = data[offset]
    result['batteriesTemperatureNumber'] = temp_count
    offset += 1

    result['cellTemperatures'] = []
    for j in range(temp_count):
        # 23, 24 - cellTemperature (x - 50)
        result['cellTemperatures'].append(struct.unpack('>H', data[offset : offset + 2])[0] - 50)
        offset += 2
    
    # 25, 26 - environmentalTemperature
    result['environmentalTemperature'] = struct.unpack('>H', data[offset : offset + 2])[0] - 50
    offset += 2

    # 25, 26 - pcbTemperature
    result['pcbTemperature'] = struct.unpack('>H', data[offset : offset + 2])[0] - 50
    offset += 2

    # 27 - maxTemperatureCellNumber
    result['maxTemperatureCellNumber'] = data[offset]
    offset += 1

    # 28 - maxTemperatureCellValue
    result['maxTemperatureCellValue'] = data[offset] - 50
    offset += 1

    # 29 - minTemperatureCellNumber
    result['minTemperatureCellNumber'] = data[offset]
    offset += 1

    # 30 - minTemperatureCellValue
    result['minTemperatureCellValue'] = data[offset] - 50
    offset += 1

    # 31 bmsFault1
    result['bmsFault1'] = hex(data[offset])
    offset += 1

    # 32 bmsFault2
    result['bmsFault2'] = hex(data[offset])
    offset += 1

    # 33 bmsAlert1
    result['bmsAlert1'] = hex(data[offset])
    offset += 1

    # 34 bmsAlert2
    result['bmsAlert2'] = hex(data[offset])
    offset += 1

    # 35 bmsAlert3
    result['bmsAlert3'] = hex(data[offset])
    offset += 1

    # 36 bmsAlert4
    result['bmsAlert4'] = hex(data[offset])
    offset += 1

    # 37, 38 u.cycleIndex
    result['cycleIndex'] = struct.unpack('>H', data[offset : offset + 2])[0]
    offset += 2

    # 39, 40 totalVoltage ( x / 100)
    result['totalVoltage'] = round(struct.unpack('>H', data[offset : offset + 2])[0] / 100.0, 2)
    offset += 2

    # 41 bmsStatus
    result['bmsStatus'] = hex(data[offset])
    offset += 1
    
    return result


class VestwoodsBMSClient:
    def __init__(
        self,
        mac_address: str,
        hass,
        mqtt_topic_prefix: str,
        logger: logging.Logger = _LOGGER,
    ):
        self.mac_address = mac_address.upper()
        self.hass = hass
        self.mqtt_topic_prefix = mqtt_topic_prefix
        self._LOGGER = logger
        self.notification_data = bytearray()
        self.client = None
        self._is_connected = False

    def on_disconnect(self, client: BleakClient):
        self._LOGGER.warning(f"Disconnected from {self.mac_address}")
        self._is_connected = False

    async def connect(self):
        self._LOGGER.info(f"Searching for device {self.mac_address}...")
        device = await BleakScanner.find_device_by_address(self.mac_address, timeout=20.0)

        if not device:
            self._LOGGER.warning(f"Could not find device with address {self.mac_address}")
            return False

        self._LOGGER.info(f"Found device: {device.name} ({device.address})")

        self.client = await establish_connection(
            BleakClient,
            device,
            name=self.mac_address,
            disconnected_callback=self.on_disconnect,
        )
        self._is_connected = self.client.is_connected
        if self._is_connected:
            self._LOGGER.info(f"Connected to {device.name} ({device.address})")
        return self._is_connected

    async def disconnect(self):
        if self.client and self._is_connected:
            await self.client.disconnect()
            self._is_connected = False
            self._LOGGER.info(f"Disconnected from {self.mac_address}")

    def _notification_handler(self, sender, data):
        """Accumulates data from notifications."""
        self.notification_data.extend(data)

    async def read_and_publish_data(self):
        if not self.client or not self._is_connected:
            self._LOGGER.warning("Not connected to BMS. Skipping data read.")
            return

        try:
            await self.client.start_notify(RX_CHAR_UUID, self._notification_handler)
            await self.client.write_gatt_char(TX_CHAR_UUID, POLL_COMMAND, response=False)
            await asyncio.sleep(2)  # Wait for notifications
            await self.client.stop_notify(RX_CHAR_UUID)

            while self.notification_data:
                start_index = self.notification_data.find(b'\x7a')
                if start_index == -1:
                    self._LOGGER.debug("No start sentinel found in buffer. Discarding.")
                    self.notification_data.clear()
                    break

                if start_index > 0:
                    self._LOGGER.debug(f"Discarding {start_index} bytes before start sentinel.")
                    self.notification_data = self.notification_data[start_index:]

                if len(self.notification_data) < 4:
                    self._LOGGER.debug("Buffer too small for header. Waiting for more data.")
                    break

                payload_len = self.notification_data[2]
                total_len = payload_len + 4

                if len(self.notification_data) < total_len:
                    self._LOGGER.debug(f"Incomplete message. Got {len(self.notification_data)}, expected {total_len}. Waiting for more data.")
                    break

                message = self.notification_data[:total_len]
                
                if not message.endswith(b'\xa7'):
                    self._LOGGER.warning("Message does not end with sentinel. Discarding.")
                    self.notification_data = self.notification_data[1:] # Discard the 0x7a and retry
                    continue

                parsed_data = parse_response(message)
                if parsed_data:
                    self._LOGGER.info("--- Parsed BMS Data ---")
                    for key, value in parsed_data.items():
                        if key == 'cellVoltages':
                            for i, voltage in enumerate(value):
                                topic = f"{self.mqtt_topic_prefix}/cellVoltage_{i+1}"
                                await mqtt.async_publish(self.hass, topic, json.dumps(voltage), qos=0, retain=False)
                        elif key == 'cellTemperatures':
                            for i, temp in enumerate(value):
                                topic = f"{self.mqtt_topic_prefix}/cellTemperature_{i+1}"
                                await mqtt.async_publish(self.hass, topic, json.dumps(temp), qos=0, retain=False)
                        else:
                            topic = f"{self.mqtt_topic_prefix}/{key}"
                            await mqtt.async_publish(self.hass, topic, json.dumps(value), qos=0, retain=False)
                else:
                    self._LOGGER.warning("Failed to parse BMS data.")
                
                self.notification_data = self.notification_data[total_len:]

        except BleakError as e:
            self._LOGGER.error(f"BLE error during read: {e}")
            await self.disconnect()

    async def run(self, refresh_interval: int = 30):
        while True:
            try:
                if not self._is_connected:
                    self._LOGGER.info("Attempting to connect to BMS...")
                    if not await self.connect():
                        self._LOGGER.error("Failed to connect to BMS. Retrying in 60 seconds...")
                        await asyncio.sleep(60)
                        continue

                await self.read_and_publish_data()

            except BleakError as e:
                self._LOGGER.error(f"BLE error during run: {e}. Attempting to reconnect in 60 seconds...")
                await self.disconnect()
                await asyncio.sleep(60)
            except Exception as e:
                self._LOGGER.error(f"An unexpected error occurred: {e}. Retrying in 60 seconds...")
                await self.disconnect()
                await asyncio.sleep(60)
            finally:
                await asyncio.sleep(refresh_interval)
