"""Test the ShieldDNS config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.shielddns.client import (
    ShieldDNSApiClientAuthenticationError,
    ShieldDNSApiClientCommunicationError,
)
from custom_components.shielddns.const import CONF_HOST, CONF_PORT, CONF_TOKEN, DOMAIN


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    config_entries.HANDLERS.pop(DOMAIN, None)

    # Needs to be imported after pop to register

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
            return_value={"Status": "OK"},
        ),
        patch(
            "custom_components.shielddns.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["step_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 443,
                CONF_TOKEN: "test-token",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ShieldDNS (192.168.1.100)"
    assert result2["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 443,
        CONF_TOKEN: "test-token",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_auth(hass: HomeAssistant) -> None:
    """Test we handle invalid auth."""
    config_entries.HANDLERS.pop(DOMAIN, None)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
        side_effect=ShieldDNSApiClientAuthenticationError,
    ):
        hass.config_entries.flow.async_configure.side_effect = AsyncMock(
            return_value={
                "type": FlowResultType.FORM,
                "errors": {"base": "invalid_auth"},
            }
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["step_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 443,
                CONF_TOKEN: "test-token",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_form_cannot_connect(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    config_entries.HANDLERS.pop(DOMAIN, None)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
        side_effect=ShieldDNSApiClientCommunicationError,
    ):
        hass.config_entries.flow.async_configure.side_effect = AsyncMock(
            return_value={
                "type": FlowResultType.FORM,
                "errors": {"base": "cannot_connect"},
            }
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["step_id"],
            {
                CONF_HOST: "192.168.1.100",
                CONF_PORT: 443,
                CONF_TOKEN: "test-token",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}
