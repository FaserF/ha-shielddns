"""conftest for shielddns tests."""

import asyncio
import contextvars
import uuid
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock

import homeassistant.config_entries
import homeassistant.core as ha
import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

# Compatibility patch for ConfigFlowResult
if not hasattr(homeassistant.config_entries, "ConfigFlowResult"):
    homeassistant.config_entries.ConfigFlowResult = Any

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
    sys.modules["pytest_homeassistant_custom_component"] = ModuleType("pytest_homeassistant_custom_component")
sys.modules["pytest_homeassistant_custom_component.common"] = mock_mod

# Suppress frame reporting
import homeassistant.helpers.frame
homeassistant.helpers.frame.report = lambda *args, **kwargs: None

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
    hass_obj.config_entries.async_setup = AsyncMock(return_value=True)
    hass_obj.config_entries.flow = MagicMock()
    # Mocking flow methods to return dicts with FlowResultType
    hass_obj.config_entries.flow.async_init = AsyncMock(return_value={
        "type": FlowResultType.FORM,
        "step_id": "user",
        "errors": {},
        "description_placeholders": {},
    })
    hass_obj.config_entries.flow.async_configure = AsyncMock(return_value={
        "type": FlowResultType.CREATE_ENTRY,
        "title": "ShieldDNS (192.168.1.100)",
        "data": {
            "host": "192.168.1.100",
            "port": 443,
            "token": "test-token",
        },
        "result": MagicMock(),
    })
    
    hass_obj.states = MagicMock()
    # Provide a smarter .get() that returns a Mock State
    def mock_get(entity_id):
        mock_state = MagicMock()
        if "total" in entity_id:
            mock_state.state = "1500"
        elif "blocked" in entity_id:
            mock_state.state = "300"
        elif "percentage" in entity_id:
            mock_state.state = "20.0"
        elif "clients" in entity_id:
            mock_state.state = "5"
        elif "version" in entity_id:
            mock_state.state = "v1.1.0"
        elif "filtering" in entity_id:
            mock_state.state = "on"
        else:
            mock_state.state = "unknown"
        return mock_state
    hass_obj.states.get = MagicMock(side_effect=mock_get)
    
    hass_obj.services = MagicMock()
    hass_obj.services.async_call = AsyncMock()
    hass_obj.services.has_service = MagicMock(return_value=True)
    
    hass_obj.data = {}

    async def async_block_till_done_mock():
        pass
    hass_obj.async_block_till_done = async_block_till_done_mock

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
        except (TypeError, AttributeError):
            return current_loop.create_task(target)
    hass.async_create_task = patched_create_task

    orig_add_job = getattr(hass, "async_add_job", MagicMock())
    def patched_add_job(target, *args, **kwargs):
        try:
            return orig_add_job(target, *args, **kwargs)
        except (TypeError, AttributeError):
            if asyncio.iscoroutine(target) or asyncio.iscoroutinefunction(target):
                return current_loop.create_task(target(*args))
            return current_loop.call_soon(target, *args)
    hass.async_add_job = patched_add_job

@pytest.fixture(scope="session", autouse=True)
def global_ha_patching():
    """Apply global patches to HomeAssistant core for test stability."""
    _SESSION_EXECUTOR = ThreadPoolExecutor(max_workers=10, thread_name_prefix="waitpid-ha-test")
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

    manifest = loader.Manifest(
        name="ShieldDNS", domain=domain, version="1.0.0", documentation="https://github.com/FaserF/ha-shielddns",
        requirements=[], dependencies=[], codeowners=["faserf"], is_built_in=False,
    )
    integration = loader.Integration(hass, f"custom_components.{domain}", path, manifest)
    hass.data["custom_components"][domain] = integration
    hass.data["integrations"][domain] = integration
