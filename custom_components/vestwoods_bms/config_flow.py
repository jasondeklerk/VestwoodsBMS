import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

class VestwoodsBMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vestwoods BMS."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["mac_address"], data=user_input)

        data_schema = vol.Schema({
            vol.Required("mac_address"): str,
            vol.Required("refresh_interval", default=30): int,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema
        )
