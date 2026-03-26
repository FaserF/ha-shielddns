"""Test ShieldDNS button."""

from unittest.mock import AsyncMock, patch

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN


async def test_button(hass: HomeAssistant) -> None:
    """Test button."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 443, CONF_TOKEN: "test"},
    )
    entry.add_to_hass(hass)

    stats_response = {}
    status_response = {"enabled": True}

    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            return_value=stats_response,
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_filtering_status",
            return_value=status_response,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entity_id = "button.shielddns_refresh_blocklists"

    state = hass.states.get(entity_id)
    assert state

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.refresh_blocklists",
        new_callable=AsyncMock,
    ) as mock_refresh:
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_refresh.assert_called_once()
