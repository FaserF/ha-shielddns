"""Test ShieldDNS sensors."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN


async def test_sensors(hass: HomeAssistant) -> None:
    """Test that sensors are created correctly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 443, CONF_TOKEN: "test"},
    )
    entry.add_to_hass(hass)

    stats_response = {
        "TotalQueries": 1000,
        "BlockedQueries": 250,
        "CacheHits": 150,
        "AverageLatency": 12.5,
    }
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

    # Total queries sensor
    state = hass.states.get("sensor.shielddns_total_queries")
    assert state
    assert state.state == "1500"

    # Blocked queries sensor
    state = hass.states.get("sensor.shielddns_blocked_queries")
    assert state
    assert state.state == "300"

    # Block percentage sensor
    state = hass.states.get("sensor.shielddns_block_percentage")
    assert state
    assert state.state == "20.0"

    # Unique clients
    state = hass.states.get("sensor.shielddns_unique_clients")
    assert state
    assert state.state == "5"

    # Versions
    state = hass.states.get("sensor.shielddns_shielddns_version")
    assert state
    assert state.state == "v1.1.0"
