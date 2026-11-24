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


async def test_hassio_discovery_aborts_when_already_configured_legacy_uid(
    hass: HomeAssistant,
) -> None:
    """Test supervisor discovery aborts and normalizes legacy port-suffixed unique_id."""
    from types import SimpleNamespace

    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.shielddns.config_flow import ShieldDNSConfigFlow

    existing = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "shieldha.tailnet.fabiseitz.de",
            CONF_PORT: 443,
            CONF_TOKEN: "tok",
        },
        entry_id="existing_addon_entry",
    )
    object.__setattr__(existing, "unique_id", "edfe50eb_shielddns_8443")
    existing.add_to_hass(hass)
    hass.config_entries.async_entries = lambda domain=None, include_ignore=None: [
        existing
    ]

    flow = ShieldDNSConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_HASSIO}

    discovery_info = SimpleNamespace(slug="edfe50eb_shielddns", uuid="abc123")
    with patch(
        "homeassistant.components.hassio.AddonManager.async_get_addon_info",
        return_value=SimpleNamespace(options={"doh_port": 443}),
    ):
        result = await flow.async_step_hassio(discovery_info)  # type: ignore[arg-type]

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    hass.config_entries.async_update_entry.assert_called_once_with(
        existing, unique_id="edfe50eb_shielddns"
    )


async def test_hassio_discovery_sets_canonical_unique_id(
    hass: HomeAssistant,
) -> None:
    """Test supervisor discovery uses slug without port as canonical unique_id."""
    from types import SimpleNamespace

    from custom_components.shielddns.config_flow import ShieldDNSConfigFlow

    hass.config_entries.async_entries = lambda domain=None, include_ignore=None: []

    flow = ShieldDNSConfigFlow()
    flow.hass = hass
    flow.context = {"source": config_entries.SOURCE_HASSIO}
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = lambda *args, **kwargs: None

    discovery_info = SimpleNamespace(slug="edfe50eb_shielddns", uuid="abc123")
    with patch(
        "homeassistant.components.hassio.AddonManager.async_get_addon_info",
        return_value=SimpleNamespace(options={"doh_port": 443}),
    ):
        result = await flow.async_step_hassio(discovery_info)  # type: ignore[arg-type]

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "hassio_confirm"
    flow.async_set_unique_id.assert_awaited_once_with("edfe50eb_shielddns")


async def test_reconfigure_updates_entry(hass: HomeAssistant) -> None:
    """Test reconfigure flow updates host, port, SSL flags and reloads."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.shielddns.config_flow import ShieldDNSConfigFlow

    existing = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "shieldha.tailnet.fabiseitz.de",
            CONF_PORT: 8443,
            CONF_TOKEN: "tok",
        },
        entry_id="reconfig_entry",
    )
    existing.add_to_hass(hass)

    flow = ShieldDNSConfigFlow()
    flow.hass = hass
    flow.context = {"source": "reconfigure", "entry_id": existing.entry_id}
    flow._get_reconfigure_entry = lambda: existing  # type: ignore[method-assign]
    flow.async_update_reload_and_abort = lambda entry, **kwargs: {  # type: ignore[method-assign]
        "type": FlowResultType.ABORT,
        "reason": "reconfigure_successful",
        "kwargs": kwargs,
    }

    with patch(
        "custom_components.shielddns.client.ShieldDNSApiClient.get_stats",
        return_value={"Status": "OK"},
    ):
        result = await flow.async_step_reconfigure(
            {
                CONF_HOST: "shieldha.tailnet.fabiseitz.de",
                CONF_PORT: 443,
                CONF_TOKEN: "tok",
                "use_ssl": True,
                "verify_ssl": True,
            }
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert result["kwargs"]["data_updates"][CONF_PORT] == 443


async def test_client_defaults_and_base_url() -> None:
    """Test client uses 30s default timeout and builds expected base URL."""
    from unittest.mock import MagicMock

    from custom_components.shielddns.client import ShieldDNSApiClient

    session = MagicMock()
    client = ShieldDNSApiClient("example.local", 443, "tok", session)
    assert client._timeout == 30
    assert client._base_url == "https://example.local:443/api"
