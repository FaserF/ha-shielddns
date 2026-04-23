"""Config flow for ShieldDNS integration."""

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import (
    ShieldDNSApiClient,
    ShieldDNSApiClientAuthenticationError,
    ShieldDNSApiClientCommunicationError,
)
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_UPDATE_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    client = ShieldDNSApiClient(
        host=data[CONF_HOST],
        port=data[CONF_PORT],
        token=data[CONF_TOKEN],
        session=session,
        use_ssl=data.get(CONF_USE_SSL, True),
        verify_ssl=data.get(CONF_VERIFY_SSL, True),
    )

    await client.get_stats()

    return {"title": f"ShieldDNS ({data[CONF_HOST]})"}


class ShieldDNSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ShieldDNS."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )
            try:
                info = await validate_input(self.hass, user_input)
            except ShieldDNSApiClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except ShieldDNSApiClientCommunicationError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                    vol.Required(CONF_TOKEN): str,
                    vol.Optional(CONF_USE_SSL, default=True): bool,
                    vol.Optional(CONF_VERIFY_SSL, default=True): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/FaserF/ha-shielddns"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Create the options flow."""
        return ShieldDNSOptionsFlowHandler()


class ShieldDNSOptionsFlowHandler(OptionsFlow):
    """Handle an options flow for ShieldDNS."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TOKEN,
                        default=self.config_entry.options.get(
                            CONF_TOKEN, self.config_entry.data.get(CONF_TOKEN)
                        ),
                    ): str,
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=1)),
                }
            ),
        )
