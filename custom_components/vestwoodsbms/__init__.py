import logging
import asyncio
import paho.mqtt.client as mqtt

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, MQTT_TOPIC_PREFIX
from .vestwoods_bms_client import VestwoodsBMSClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vestwoods BMS from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    mac_address = entry.data["mac_address"]
    refresh_interval = entry.data["refresh_interval"]

    bms_client = VestwoodsBMSClient(
        mac_address=mac_address,
        hass=hass,
        mqtt_topic_prefix=f"{MQTT_TOPIC_PREFIX}/{mac_address.replace(':', '_')}",
        logger=_LOGGER,
    )

    # Start the BMS client in a background task
    hass.data[DOMAIN][entry.entry_id] = {
        "bms_client": bms_client,
        "task": hass.async_create_task(bms_client.run(refresh_interval)),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        bms_client_task = data["task"]

        bms_client_task.cancel()
        try:
            await bms_client_task  # Wait for the task to finish cancelling
        except asyncio.CancelledError:
            _LOGGER.info("BMS client task cancelled successfully.")

    return unload_ok