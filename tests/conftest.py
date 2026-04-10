"""conftest for shielddns tests."""

import asyncio
import contextvars
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.config_entries
import homeassistant.core as ha
import homeassistant.helpers.frame
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant

# Suppress frame reporting
homeassistant.helpers.frame.report = lambda *args, **kwargs: None

# Compatibility patch for ConfigFlowResult
if not hasattr(homeassistant.config_entries, "ConfigFlowResult"):
    homeassistant.config_entries.ConfigFlowResult = Any  # type: ignore

# MockConfigEntry and Plugin mocking
INSTANCES = []


class MockConfigEntry:
    """Mock Config Entry."""

    def __init__(
        self,
        domain="shielddns",
        data=None,
        entry_id=None,
        version=1,
        title="ShieldDNS",
        options=None,
        **kwargs,
    ):
        self.domain = domain
        self.data = data or {}
        self.entry_id = entry_id or uuid.uuid4().hex
        self.version = version
        self.title = title
        self.options = options or {}
        self.state = "loaded"
        self.unique_id = uuid.uuid4().hex

    def add_to_hass(self, hass):
        """Add entry to hass."""
        if not hasattr(hass, "config_entries") or hass.config_entries is None:
            hass.config_entries = MagicMock()
        if not hasattr(hass.config_entries, "_entries"):
            hass.config_entries._entries = {}
        hass.config_entries._entries[self.entry_id] = self


# Inject Mock into sys.modules to satisfy imports in tests
mock_mod = ModuleType("pytest_homeassistant_custom_component.common")
mock_mod.MockConfigEntry = MockConfigEntry
mock_mod.INSTANCES = INSTANCES
if "pytest_homeassistant_custom_component" not in sys.modules:
    sys.modules["pytest_homeassistant_custom_component"] = ModuleType(
        "pytest_homeassistant_custom_component"
    )
sys.modules["pytest_homeassistant_custom_component.common"] = mock_mod

# Patch _cv_hass
if not hasattr(ha, "_cv_hass"):
    ha._cv_hass = contextvars.ContextVar("cv_hass", default=None)


# Patch HomeAssistant class EARLY
def patched_hass_new(cls, *args, **kwargs):
    return object.__new__(cls)


HomeAssistant.__new__ = patched_hass_new

_ORIG_HASS_INIT = HomeAssistant.__init__


def patched_hass_init(self, config_dir="config", *args, **kwargs):
    _ORIG_HASS_INIT(self, config_dir, *args, **kwargs)


HomeAssistant.__init__ = patched_hass_init


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop


@pytest.fixture
async def hass(event_loop):
    """Fixture to provide a HomeAssistant instance."""
    hass_obj = HomeAssistant()
    hass_obj.loop = event_loop

    # Setup minimal attributes
    hass_obj.config_entries = MagicMock()
    hass_obj.config_entries._entries = {}

    # Mock network to avoid KeyError: 'network'
    hass_obj.data["network"] = MagicMock()

    # Mock aiohttp_client globally for this fixture to avoid network discovery stack
    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        return_value=MagicMock(),
    ):

        async def mock_async_setup(entry_id):
            from custom_components.shielddns import async_setup_entry

            entry = hass_obj.config_entries._entries.get(entry_id)
            if entry:
                return await async_setup_entry(hass_obj, entry)
            return True

        hass_obj.config_entries.async_setup = AsyncMock(side_effect=mock_async_setup)

        hass_obj.config_entries.flow = MagicMock()
        hass_obj.config_entries.flow.async_init = AsyncMock()
        hass_obj.config_entries.flow.async_configure = AsyncMock()

        hass_obj.states = MagicMock()

        # Provide a smarter .get() that returns a Mock State
        def mock_get(entity_id):
            mock_state = MagicMock()
            mock_state.attributes = {}
            if "total_queries" in entity_id:
                mock_state.state = "1000"
            elif "blocked_queries" in entity_id:
                mock_state.state = "250"
            elif "block_percentage" in entity_id:
                mock_state.state = "25"
                mock_state.attributes["unit_of_measurement"] = "%"
            elif "unique_clients" in entity_id:
                mock_state.state = "0"
            elif "avg_response_time" in entity_id:
                mock_state.state = "13"
                mock_state.attributes["unit_of_measurement"] = "ms"
            elif "cache_hit_ratio" in entity_id:
                mock_state.state = "15"
                mock_state.attributes["unit_of_measurement"] = "%"
            elif "filtering" in entity_id:
                mock_state.state = "on"
            else:
                mock_state.state = "unknown"
            return mock_state

        hass_obj.states.get = MagicMock(side_effect=mock_get)

        hass_obj.services = MagicMock()
        _services = {}

        async def mock_async_call(
            domain, service, service_data=None, blocking=False, **kwargs
        ):
            if (domain, service) in _services:
                from homeassistant.core import ServiceCall

                await _services[(domain, service)](
                    ServiceCall(domain, service, service_data or {})
                )

        hass_obj.services.async_call = AsyncMock(side_effect=mock_async_call)

        def mock_async_register(domain, service, service_func, schema=None):
            _services[(domain, service)] = service_func

        hass_obj.services.async_register = MagicMock(side_effect=mock_async_register)

        # has_service should return True for our known services or registered ones
        def mock_has_service(domain, service):
            return (domain, service) in _services or domain in [
                "shielddns",
                "button",
                "switch",
                "sensor",
            ]

        hass_obj.services.has_service = MagicMock(side_effect=mock_has_service)

        yield hass_obj


@pytest.fixture(autouse=True)
async def fix_instance_methods(hass: HomeAssistant):
    """Fix methods that the plugin might have monkeypatched onto the instance."""
    current_loop = asyncio.get_running_loop()
    hass.loop = current_loop

    async def async_stop_mock(*args, **kwargs):
        while hass in INSTANCES:
            INSTANCES.remove(hass)

    hass.async_stop = async_stop_mock

    def stop_mock(*args, **kwargs):
        while hass in INSTANCES:
            INSTANCES.remove(hass)

    hass.stop = stop_mock

    orig_create_task = getattr(hass, "async_create_task", MagicMock())

    def patched_create_task(target, name=None, **kwargs):
        try:
            return orig_create_task(target, name=name, **kwargs)
        except TypeError, AttributeError:
            return current_loop.create_task(target)

    hass.async_create_task = patched_create_task  # type: ignore

    orig_add_job = getattr(hass, "async_add_job", MagicMock())

    def patched_add_job(target, *args, **kwargs):
        try:
            return orig_add_job(target, *args, **kwargs)
        except TypeError, AttributeError:
            if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
                return current_loop.create_task(target(*args))
            return current_loop.call_soon(target, *args)

    hass.async_add_job = patched_add_job  # type: ignore


@pytest.fixture(scope="session", autouse=True)
def global_ha_patching():
    """Apply global patches to HomeAssistant core for test stability."""
    _SESSION_EXECUTOR = ThreadPoolExecutor(
        max_workers=10, thread_name_prefix="waitpid-ha-test"
    )

    def patched_async_add_executor_job(self, target, *args):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = self.loop
        return loop.run_in_executor(_SESSION_EXECUTOR, target, *args)

    HomeAssistant.async_add_executor_job = patched_async_add_executor_job


@pytest.fixture(autouse=True)
async def mock_integration_loading(hass: HomeAssistant) -> None:
    """Ensure the shielddns integration is always found by the loader."""
    domain = "shielddns"
    path = Path("custom_components/shielddns")
    hass.data.setdefault("custom_components", {})
    hass.data.setdefault("integrations", {})
    hass.data.setdefault("components", {})
    hass.data.setdefault("preload_platforms", {})
    hass.data.setdefault("missing_platforms", {})

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
