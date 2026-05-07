"""Diagnostics support for ShieldDNS."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator

REDACT_CONFIG = {CONF_TOKEN}
REDACT_STATS = {"admin_password_hashed"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    diagnostics_data = {
        "config_entry": async_redact_data(config_entry.as_dict(), REDACT_CONFIG),
        "coordinator_data": coordinator.data,
    }

    try:
        backend_diagnostics = await coordinator.client.get_diagnostics()
        diagnostics_data["backend_diagnostics"] = async_redact_data(
            backend_diagnostics, REDACT_STATS
        )
    except Exception:  # pylint: disable=broad-except
        diagnostics_data["backend_diagnostics"] = {
            "error": "Could not fetch backend diagnostics"
        }

    return diagnostics_data
