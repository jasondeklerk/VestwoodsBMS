from __future__ import annotations

import logging

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import DOMAIN, MQTT_TOPIC_PREFIX

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MQTT sensors from a config entry."""
    mac_address = config_entry.data["mac_address"]
    mqtt_topic_prefix = f"{MQTT_TOPIC_PREFIX}/{mac_address.replace(':', '_')}"
    num_cells = config_entry.data.get("number_of_cells", 16)
    num_temp_sensors = config_entry.data.get("number_of_temperature_sensors", 4)

    sensors_to_add = []

    # Core BMS sensors
    sensors_to_add.extend([
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "totalVoltage", "Total Voltage", "V", "voltage"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "soc", "State of Charge", "%", "battery"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "totalCurrent", "Total Current", "A", "current"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "environmentalTemperature", "Environmental Temperature", "°C", "temperature"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "pcbTemperature", "PCB Temperature", "°C", "temperature"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "soh", "State of Health", "%", None
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "actualCapacity", "Actual Capacity", "Ah", None
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "surplusCapacity", "Surplus Capacity", "Ah", None
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "nominalCapacity", "Nominal Capacity", "Ah", None
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "cycleIndex", "Cycle Index", "cycles", None
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "maxCellVoltage", "Max Cell Voltage", "V", "voltage"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "minCellVoltage", "Min Cell Voltage", "V", "voltage"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "maxTemperatureCellValue", "Max Temperature", "°C", "temperature"
        ),
        VestwoodsBMSSensor(
            hass, config_entry, mqtt_topic_prefix, "minTemperatureCellValue", "Min Temperature", "°C", "temperature"
        ),
    ])

    # Dynamically add cell voltage sensors
    for i in range(1, num_cells + 1):
        sensors_to_add.append(
            VestwoodsBMSSensor(
                hass, config_entry, mqtt_topic_prefix, f"cellVoltage_{i}", f"Cell {i} Voltage", "V", "voltage"
            )
        )

    # Dynamically add cell temperature sensors
    for i in range(1, num_temp_sensors + 1):
        sensors_to_add.append(
            VestwoodsBMSSensor(
                hass, config_entry, mqtt_topic_prefix, f"cellTemperature_{i}", f"Cell {i} Temperature", "°C", "temperature"
            )
        )

    async_add_entities(sensors_to_add)


class VestwoodsBMSSensor(SensorEntity):
    """Representation of a Vestwoods BMS MQTT Sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        mqtt_topic_prefix: str,
        key: str,
        name: str,
        unit: str,
        device_class: str | None,
    ) -> None:
        self._hass = hass
        self._config_entry = config_entry
        self._mqtt_topic = f"{mqtt_topic_prefix}/{key}"
        self._attr_name = f"Vestwoods BMS {config_entry.data["mac_address"]} {name}"
        self._attr_unique_id = f"{config_entry.entry_id}-{key}"
        self._attr_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT events."""

        @callback
        def message_received(message):
            """Handle new MQTT messages."""
            try:
                self._attr_state = float(message.payload)
                self.async_write_ha_state()
            except ValueError:
                _LOGGER.warning("Could not parse payload as float: %s", message.payload)

        await mqtt.async_subscribe(self._hass, self._mqtt_topic, message_received, 1)

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": f"Vestwoods BMS {self._config_entry.data["mac_address"]}",
            "manufacturer": "Vestwoods",
            "model": "BMS",
        }