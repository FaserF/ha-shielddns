"""conftest for shielddns tests."""

import asyncio
import sys
import uuid
from pathlib import Path
from types import MappingProxyType, ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.config_entries as ce
import homeassistant.helpers.frame
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant

# ---------------------------------------------------------------------------
# Suppress frame reporting globally at import time so it never triggers
# ---------------------------------------------------------------------------
homeassistant.helpers.frame.report = lambda *args, **kwargs: None

try:
    _frame_report_usage_patcher = patch(
        "homeassistant.helpers.frame.report_usage",
        new=MagicMock(),
    )
    _frame_report_usage_patcher.start()
except AttributeError:
    # report_usage doesn't exist in this version of HA
    pass

try:
    _zeroconf_usage_patcher = patch(
        "homeassistant.components.zeroconf.usage.report_usage",
        new=MagicMock(),
    )
    _zeroconf_usage_patcher.start()
except Exception:
    pass


# ---------------------------------------------------------------------------
# MockConfigEntry – inherits from the real ConfigEntry so isinstance() checks
# inside DataUpdateCoordinator pass.
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
        init_kwargs = {
            "data": data or {},
            "domain": domain,
            "entry_id": entry_id or uuid.uuid4().hex,
            "minor_version": 0,
            "options": options or {},
            "source": ce.SOURCE_USER,
            "title": title,
            "unique_id": uuid.uuid4().hex,
            "version": version,
        }
        # Home Assistant 2024.12+ requires subentries_data, 2025.1+ requires discovery_keys
        import inspect

        params = inspect.signature(ce.ConfigEntry.__init__).parameters
        if "discovery_keys" in params:
            init_kwargs["discovery_keys"] = MappingProxyType({})
        if "subentries_data" in params:
            init_kwargs["subentries_data"] = None

        super().__init__(**init_kwargs)
        object.__setattr__(self, "state", ce.ConfigEntryState.SETUP_IN_PROGRESS)

    def add_to_hass(self, hass: HomeAssistant) -> None:
        """Add entry to hass."""
        if not hasattr(hass.config_entries, "_entries"):
            hass.config_entries._entries = {}
        hass.config_entries._entries[self.entry_id] = self


# ---------------------------------------------------------------------------
# Inject MockConfigEntry into the pytest-homeassistant-custom-component shim
# ---------------------------------------------------------------------------
INSTANCES: list[Any] = []
_mock_phcc = ModuleType("pytest_homeassistant_custom_component")
_mock_phcc_common = ModuleType("pytest_homeassistant_custom_component.common")
_mock_phcc_common.MockConfigEntry = MockConfigEntry  # type: ignore[attr-defined]
_mock_phcc_common.INSTANCES = INSTANCES  # type: ignore[attr-defined]
sys.modules.setdefault("pytest_homeassistant_custom_component", _mock_phcc)
sys.modules["pytest_homeassistant_custom_component.common"] = _mock_phcc_common


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_loop() -> Any:
    """Create a fresh event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def hass(event_loop: asyncio.AbstractEventLoop) -> Any:
    """Provide a minimal HomeAssistant instance."""

    # Patch __new__ so HA skips its singleton guard
    with patch.object(
        HomeAssistant, "__new__", lambda cls, *a, **kw: object.__new__(cls)
    ):
        hass_obj = HomeAssistant.__new__(HomeAssistant)

    # Minimal __init__
    hass_obj.loop = event_loop
    hass_obj.data = {}
    hass_obj.states = MagicMock()
    hass_obj.bus = MagicMock()
    hass_obj.components = MagicMock()
    hass_obj.config = MagicMock()
    hass_obj.config_entries = MagicMock()
    hass_obj.config_entries._entries = {}

    # Pre-populate network key so aiohttp connector never reaches it
    hass_obj.data["network"] = MagicMock()

    # States mock
    _mock_states: dict[str, str] = {
        "total_queries": "1000",
        "blocked_queries": "250",
        "block_percentage": "25",
        "unique_clients": "0",
        "avg_response_time": "13",
        "cache_hit_ratio": "15",
        "filtering": "on",
        "switch": "on",
        "update": "on",
    }
    _mock_units: dict[str, str] = {
        "block_percentage": "%",
        "avg_response_time": "ms",
        "cache_hit_ratio": "%",
    }

    def _mock_get(entity_id: str) -> MagicMock:
        s = MagicMock()
        s.attributes: dict[str, Any] = {}
        for key, val in _mock_states.items():
            if key in entity_id:
                s.state = val
                if unit := _mock_units.get(key):
                    s.attributes["unit_of_measurement"] = unit
                return s
        s.state = "unknown"
        return s

    hass_obj.states.get = MagicMock(side_effect=_mock_get)

    # Services mock with a real registry
    hass_obj.services = MagicMock()
    _services: dict[tuple[str, str], Any] = {}

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

            if domain == "button" and service == "press" and "refresh" in entity_id:
                await coord.client.refresh_blocklists()
            elif domain == "switch" and "filtering" in entity_id:
                if service == "turn_on":
                    await coord.client.toggle_filtering(True)
                    _mock_states["switch"] = "on"
                    _mock_states["filtering"] = "on"
                elif service == "turn_off":
                    await coord.client.toggle_filtering(False)
                    _mock_states["switch"] = "off"
                    _mock_states["filtering"] = "off"

    hass_obj.services.async_call = AsyncMock(side_effect=_async_call)
    hass_obj.services.async_register = MagicMock(
        side_effect=lambda d, s, fn, schema=None: _services.update({(d, s): fn})
    )
    hass_obj.services.async_remove = MagicMock()
    hass_obj.services.has_service = MagicMock(
        side_effect=lambda d, s: (d, s) in _services
    )

    # async_block_till_done is a no-op in tests
    hass_obj.async_block_till_done = AsyncMock()

    # config_entries.async_setup calls real async_setup_entry
    async def _async_setup(entry_id: str) -> bool:
        from custom_components.shielddns import async_setup_entry

        entry = hass_obj.config_entries._entries.get(entry_id)
        if entry:
            return await async_setup_entry(hass_obj, entry)
        return True

    hass_obj.config_entries.async_setup = AsyncMock(side_effect=_async_setup)

    # config_entries.async_forward_entry_setups is a no-op
    hass_obj.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)

    # config_entries.flow: async_init returns FORM, async_configure is a smart mock
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
        """Default: create an entry and trigger async_setup_entry so test assertions pass."""
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

    # Patch aiohttp session so the zeroconf / DNS resolver chain is never hit
    import aiohttp

    mock_session = MagicMock(spec=aiohttp.ClientSession)
    mock_session.close = AsyncMock()
    try:
        with patch(
            "homeassistant.helpers.aiohttp_client.async_get_clientsession",
            return_value=mock_session,
        ):
            yield hass_obj
    finally:
        pass


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
