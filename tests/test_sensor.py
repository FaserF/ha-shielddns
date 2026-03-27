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
    assert state.state == "1000"

    # Blocked queries sensor
    state = hass.states.get("sensor.shielddns_blocked_queries")
    assert state
    assert state.state == "250"

    # Block percentage sensor
    state = hass.states.get("sensor.shielddns_block_percentage")
    assert state
    assert state.state == "25.0"

    # Unique clients
    state = hass.states.get("sensor.shielddns_unique_clients")
    assert state
    assert state.state == "0"

    # Avg. Response Time
    state = hass.states.get("sensor.shielddns_avg_response_time")
    assert state
    assert state.state == "12.5"
    assert state.attributes.get("unit_of_measurement") == "ms"

    # Cache Hit Ratio
    state = hass.states.get("sensor.shielddns_cache_hit_ratio")
    assert state
    assert state.state == "15.0"
    assert state.attributes.get("unit_of_measurement") == "%"
