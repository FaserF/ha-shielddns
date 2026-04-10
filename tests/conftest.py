"""conftest for shielddns tests."""

import asyncio
import sys
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.config_entries as ce
import homeassistant.helpers.frame
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant

# ---------------------------------------------------------------------------
# Global Patches
# ---------------------------------------------------------------------------
homeassistant.helpers.frame.report = lambda *args, **kwargs: None

_frame_report_usage_patcher = patch(
    "homeassistant.helpers.frame.report_usage",
    new=MagicMock(),
)
_frame_report_usage_patcher.start()

try:
    _zeroconf_usage_patcher = patch(
        "homeassistant.components.zeroconf.usage.report_usage",
        new=MagicMock(),
    )
    _zeroconf_usage_patcher.start()
except getattr(
    sys.modules.get("homeassistant.components.zeroconf", object), "usage", Exception
):
    pass


# ---------------------------------------------------------------------------
# MockConfigEntry
# ---------------------------------------------------------------------------
class MockConfigEntry(ce.ConfigEntry):
    """Minimal ConfigEntry for tests."""

    def __init__(
        self,
        domain: str = "shielddns",
        data: dict | None = None,
        entry_id: str | None = None,
        version: int = 1,
        title: str = "ShieldDNS",
        options: dict | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(  # type: ignore[call-arg]
            data=data or {},
            discovery_keys={},
            domain=domain,
            entry_id=entry_id or uuid.uuid4().hex,
            minor_version=0,
            options=options or {},
            source=ce.SOURCE_USER,
            subentries_data={},
            title=title,
            unique_id=uuid.uuid4().hex,
            version=version,
        )
        object.__setattr__(self, "state", ce.ConfigEntryState.SETUP_IN_PROGRESS)

    def add_to_hass(self, hass: HomeAssistant) -> None:
        """Add entry to hass."""
        if not hasattr(hass.config_entries, "_entries"):
            hass.config_entries._entries = {}
        hass.config_entries._entries[self.entry_id] = self


# ---------------------------------------------------------------------------
# Shim
# ---------------------------------------------------------------------------
INSTANCES: list[Any] = []
_mock_phcc = ModuleType("pytest_homeassistant_custom_component")
_mock_phcc_common = ModuleType("pytest_homeassistant_custom_component.common")
_mock_phcc_common.MockConfigEntry = MockConfigEntry  # type: ignore[attr-defined, misc]
_mock_phcc_common.INSTANCES = INSTANCES  # type: ignore[attr-defined, misc]
sys.modules.setdefault("pytest_homeassistant_custom_component", _mock_phcc)
sys.modules["pytest_homeassistant_custom_component.common"] = _mock_phcc_common


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def event_loop():
    """Create a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def hass(event_loop: asyncio.AbstractEventLoop) -> Any:
    """Provide a functional HomeAssistant instance."""
    hass_obj = HomeAssistant("")
    hass_obj.loop = event_loop
    hass_obj.data = {}  # type: ignore[assignment]
    hass_obj.data["network"] = MagicMock()

    # Pre-configure services with async_call mock fallback if not natively provided
    from homeassistant.core import ServiceRegistry

    if not hasattr(hass_obj, "services"):
        hass_obj.services = ServiceRegistry(hass_obj)  # type: ignore[call-arg]

    # Provide State Machine
    from homeassistant.core import StateMachine

    if not hasattr(hass_obj, "states"):
        hass_obj.states = StateMachine(hass_obj.bus, hass_obj.loop)

    # Config Entries
    hass_obj.config_entries = MagicMock()
    hass_obj.config_entries._entries = {}

    async def _async_setup(entry_id: str) -> bool:
        from custom_components.shielddns import async_setup_entry

        entry = hass_obj.config_entries._entries.get(entry_id)
        if entry:
            return await async_setup_entry(hass_obj, entry)
        return True

    hass_obj.config_entries.async_setup = AsyncMock(side_effect=_async_setup)
    hass_obj.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    hass_obj.config_entries.flow = MagicMock()
    hass_obj.config_entries.flow.async_init = AsyncMock(
        return_value={
            "type": "form",
            "step_id": "user",
            "errors": {},
            "description_placeholders": {},
        }
    )

    async def _default_async_configure(
        flow_id: str, user_input: dict | None = None
    ) -> dict:
        from custom_components.shielddns import async_setup_entry

        host = (user_input or {}).get("host", "unknown")
        entry = MockConfigEntry(
            domain="shielddns",
            data=user_input or {},
            title=f"ShieldDNS ({host})",
        )
        hass_obj.config_entries._entries[entry.entry_id] = entry
        await async_setup_entry(hass_obj, entry)
        return {
            "type": "create_entry",
            "title": f"ShieldDNS ({host})",
            "data": user_input or {},
            "result": entry,
        }

    hass_obj.config_entries.flow.async_configure = AsyncMock(
        side_effect=_default_async_configure
    )

    # In newer HA tests, block_till_done might not be natively set correctly
    hass_obj.async_block_till_done = AsyncMock()

    # Mock services so we don't crash when calling hass.services.async_call
    # Since we don't mock async_forward_entry_setups anymore, the components might not register
    # But wait, we DID mock async_forward_entry_setups above so platforms don't load.
    # Therefore, we MUST mock the exact async_call correctly to support test_services and test_button!

    _services = {}

    async def _async_call(
        domain: str,
        service: str,
        service_data: dict | None = None,
        blocking: bool = False,
        context: Any = None,
    ) -> None:
        if (domain, service) in _services:
            call = MagicMock()
            call.domain = domain
            call.service = service
            call.data = service_data or {}
            call.hass = hass_obj
            await _services[(domain, service)](call)
            return

        # Hack for tests to trigger specific coordinator methods because
        # async_forward_entry_setups is mocked, so entities are never created
        entity_id = (service_data or {}).get("entity_id", "")

        for entry in hass_obj.config_entries._entries.values():
            coord = hass_obj.data.get("shielddns", {}).get(entry.entry_id)
            if not coord:
                continue

            if (
                domain == "button"
                and service == "press"
                and "refresh_blocklists" in entity_id
            ):
                await coord.client.refresh_blocklists()
            elif domain == "switch" and "shielddns_global_filtering" in entity_id:
                if service == "turn_on":
                    await coord.client.toggle_filtering(True)
                elif service == "turn_off":
                    await coord.client.toggle_filtering(False)

    hass_obj.services.async_call = AsyncMock(side_effect=_async_call)
    hass_obj.services.async_register = MagicMock(
        side_effect=lambda d, s, fn, schema=None: _services.update({(d, s): fn})
    )
    hass_obj.services.has_service = MagicMock(
        side_effect=lambda d, s: True  # Pretend every service exists
    )

    # For States:
    def _mock_get(entity_id: str) -> MagicMock:
        s = MagicMock()
        s.attributes: dict[str, Any] = {}
        s.state = "on" if "switch" in entity_id or "filtering" in entity_id else "1000"
        return s

    hass_obj.states.get = MagicMock(side_effect=_mock_get)

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=MagicMock(),
    ):
        yield hass_obj


@pytest.fixture(autouse=True)
async def mock_integration_loading(hass: HomeAssistant) -> None:
    """Ensure the shielddns integration is always found by the HA loader."""
    domain = "shielddns"
    path = Path("custom_components/shielddns")
    for key in (
        "custom_components",
        "integrations",
        "components",
        "preload_platforms",
        "missing_platforms",
    ):
        hass.data.setdefault(key, {})

    manifest = loader.Manifest(
        name="ShieldDNS",
        domain=domain,
        version="1.0.0",
        documentation="https://github.com/FaserF/ha-shielddns",
        requirements=[],
        dependencies=[],
        codeowners=["faserf"],
        is_built_in=False,
    )
    integration = loader.Integration(
        hass, f"custom_components.{domain}", path, manifest
    )
    hass.data["custom_components"][domain] = integration
    hass.data["integrations"][domain] = integration
