"""Test ShieldDNS switch."""

from unittest.mock import patch

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
)
from homeassistant.components.switch import (
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN


async def test_switch(hass: HomeAssistant) -> None:
    """Test switch."""
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

    entity_id = "switch.shielddns_global_filtering"

    # Test initial state
    state = hass.states.get(entity_id)
    assert state
    assert state.state == "on"

    # Test turning off
    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.toggle_filtering",
            new_callable=AsyncMock,
        ) as mock_toggle,
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            new_callable=AsyncMock,
            return_value=stats_response,
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_filtering_status",
            new_callable=AsyncMock,
            return_value={"enabled": False},
        ),
    ):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_toggle.assert_called_once_with(False)
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "off"

    # Test turning on
    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.toggle_filtering",
            new_callable=AsyncMock,
        ) as mock_toggle,
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            new_callable=AsyncMock,
            return_value=stats_response,
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_filtering_status",
            new_callable=AsyncMock,
            return_value={"enabled": True},
        ),
    ):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        mock_toggle.assert_called_once_with(True)
        await hass.async_block_till_done()
        state = hass.states.get(entity_id)
        assert state
        assert state.state == "on"
