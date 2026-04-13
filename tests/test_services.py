"""Test ShieldDNS services."""

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN


async def test_services(hass: HomeAssistant) -> None:
    """Test domain blocking and allowing services."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 443, CONF_TOKEN: "test"},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            return_value={},
        ),
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_filtering_status",
            return_value={"enabled": True},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # Ensure services are registered
    assert hass.services.has_service(DOMAIN, "block_domain")
    assert hass.services.has_service(DOMAIN, "allow_domain")
    assert hass.services.has_service(DOMAIN, "remove_rule")

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.add_rule",
        new_callable=AsyncMock,
    ) as mock_add_rule:
        await hass.services.async_call(
            DOMAIN,
            "block_domain",
            {"domain": "tiktok.com"},
            blocking=True,
        )
        mock_add_rule.assert_called_once_with("tiktok.com", "block")

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.add_rule",
        new_callable=AsyncMock,
    ) as mock_add_rule:
        await hass.services.async_call(
            DOMAIN,
            "allow_domain",
            {"domain": "netflix.com"},
            blocking=True,
        )
        mock_add_rule.assert_called_once_with("netflix.com", "allow")

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.remove_rule",
        new_callable=AsyncMock,
    ) as mock_remove_rule:
        await hass.services.async_call(
            DOMAIN,
            "remove_rule",
            {"domain": "ads.com"},
            blocking=True,
        )
        mock_remove_rule.assert_called_once_with("ads.com")
