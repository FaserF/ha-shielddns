"""The ShieldDNS integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import ShieldDNSApiClient
from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_UPDATE_INTERVAL,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import ShieldDNSDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.BUTTON,
]

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
    client = ShieldDNSApiClient(
        host,
        port,
        entry.options.get(CONF_TOKEN, entry.data.get(CONF_TOKEN)),
        session=session,
        use_ssl=entry.data.get(CONF_USE_SSL, True),
        verify_ssl=entry.data.get(CONF_VERIFY_SSL, True),
    )

    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    coordinator = ShieldDNSDataUpdateCoordinator(
        hass, entry, client, host, port, update_interval
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register Services
    async def async_block_domain(call: ServiceCall) -> None:
        """Block a domain via ShieldDNS."""
        from homeassistant.helpers.service import async_extract_config_entry_ids

        entry_ids = await async_extract_config_entry_ids(call)
        for entry_id in entry_ids or hass.data[DOMAIN]:
            if coord := hass.data[DOMAIN].get(entry_id):
                await coord.client.add_rule(call.data["domain"], "block")

    async def async_allow_domain(call: ServiceCall) -> None:
        """Allow a domain via ShieldDNS."""
        from homeassistant.helpers.service import async_extract_config_entry_ids

        entry_ids = await async_extract_config_entry_ids(call)
        for entry_id in entry_ids or hass.data[DOMAIN]:
            if coord := hass.data[DOMAIN].get(entry_id):
                await coord.client.add_rule(call.data["domain"], "allow")

    async def async_remove_rule(call: ServiceCall) -> None:
        """Remove a domain rule via ShieldDNS."""
        from homeassistant.helpers.service import async_extract_config_entry_ids

        entry_ids = await async_extract_config_entry_ids(call)
        for entry_id in entry_ids or hass.data[DOMAIN]:
            if coord := hass.data[DOMAIN].get(entry_id):
                await coord.client.remove_rule(call.data["domain"])

    if not hass.services.has_service(DOMAIN, SERVICE_BLOCK_DOMAIN):
        hass.services.async_register(
            DOMAIN, SERVICE_BLOCK_DOMAIN, async_block_domain, schema=DOMAIN_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_ALLOW_DOMAIN):
        hass.services.async_register(
            DOMAIN, SERVICE_ALLOW_DOMAIN, async_allow_domain, schema=DOMAIN_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_REMOVE_RULE):
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


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)
