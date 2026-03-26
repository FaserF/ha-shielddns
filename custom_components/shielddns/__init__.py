"""The ShieldDNS integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import ShieldDNSApiClient
from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]

SERVICE_BLOCK_DOMAIN = "block_domain"
SERVICE_ALLOW_DOMAIN = "allow_domain"
SERVICE_REMOVE_RULE = "remove_rule"

DOMAIN_SCHEMA = vol.Schema(
    {
        vol.Required("domain"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ShieldDNS from a config entry."""
    session = async_get_clientsession(hass)
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    client = ShieldDNSApiClient(host, port, entry.data[CONF_TOKEN], session=session)

    coordinator = ShieldDNSDataUpdateCoordinator(hass, client, host, port)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register Services
    async def async_block_domain(call: ServiceCall) -> None:
        """Block a domain via ShieldDNS."""
        for _, coord in hass.data[DOMAIN].items():
            await coord.client.add_rule(call.data["domain"], "block")

    async def async_allow_domain(call: ServiceCall) -> None:
        """Allow a domain via ShieldDNS."""
        for _, coord in hass.data[DOMAIN].items():
            await coord.client.add_rule(call.data["domain"], "allow")

    async def async_remove_rule(call: ServiceCall) -> None:
        """Remove a domain rule via ShieldDNS."""
        for _, coord in hass.data[DOMAIN].items():
            await coord.client.remove_rule(call.data["domain"])

    hass.services.async_register(
        DOMAIN, SERVICE_BLOCK_DOMAIN, async_block_domain, schema=DOMAIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ALLOW_DOMAIN, async_allow_domain, schema=DOMAIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_RULE, async_remove_rule, schema=DOMAIN_SCHEMA
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_BLOCK_DOMAIN)
        hass.services.async_remove(DOMAIN, SERVICE_ALLOW_DOMAIN)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_RULE)

    return unload_ok
