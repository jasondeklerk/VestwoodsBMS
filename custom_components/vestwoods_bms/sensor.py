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
    data = hass.data[DOMAIN][config_entry.entry_id]
    mac_address = config_entry.data["mac_address"]
    mqtt_topic_prefix = f"{MQTT_TOPIC_PREFIX}/{mac_address.replace(':', '_')}"

    sensors_to_add = []

    # Example: Add a sensor for total voltage
    sensors_to_add.append(
        VestwoodsBMSSensor(
            hass,
            config_entry,
            mqtt_topic_prefix,
            "totalVoltage",
            "Total Voltage",
            "V",
            "voltage",
        )
    )
    # Example: Add a sensor for State of Charge (SOC)
    sensors_to_add.append(
        VestwoodsBMSSensor(
            hass,
            config_entry,
            mqtt_topic_prefix,
            "soc",
            "State of Charge",
            "%",
            "battery",
        )
    )
    # Example: Add a sensor for totalCurrent
    sensors_to_add.append(
        VestwoodsBMSSensor(
            hass,
            config_entry,
            mqtt_topic_prefix,
            "totalCurrent",
            "Total Current",
            "A",
            "current",
        )
    )
    # Example: Add a sensor for environmentalTemperature
    sensors_to_add.append(
        VestwoodsBMSSensor(
            hass,
            config_entry,
            mqtt_topic_prefix,
            "environmentalTemperature",
            "Environmental Temperature",
            "°C",
            "temperature",
        )
    )
    # Example: Add a sensor for pcbTemperature
    sensors_to_add.append(
        VestwoodsBMSSensor(
            hass,
            config_entry,
            mqtt_topic_prefix,
            "pcbTemperature",
            "PCB Temperature",
            "°C",
            "temperature",
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
        device_class: str,
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
