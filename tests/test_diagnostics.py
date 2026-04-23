"""Test ShieldDNS diagnostics."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN
from custom_components.shielddns.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 443, CONF_TOKEN: "test-token"},
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    stats_response = {"version": "v1.6.5", "total_queries": 100}
    status_response = {"enabled": True}
    backend_diag = {"admin_password_hashed": "SECRET", "system_info": "Linux"}

    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            return_value=stats_response,
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_filtering_status",
            return_value=status_response,
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_diagnostics",
            return_value=backend_diag,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        diagnostics = await async_get_config_entry_diagnostics(hass, entry)

        assert diagnostics["config_entry"]["data"][CONF_TOKEN] == "**REDACTED**"
        assert diagnostics["coordinator_data"]["stats"] == stats_response
        assert (
            diagnostics["backend_diagnostics"]["admin_password_hashed"]
            == "**REDACTED**"
        )
        assert diagnostics["backend_diagnostics"]["system_info"] == "Linux"
