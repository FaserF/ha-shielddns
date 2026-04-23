"""Button platform for ShieldDNS."""

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator
from .entity import ShieldDNSEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShieldDNS button based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            ShieldDNSRefreshListsButton(coordinator, entry.entry_id),
            ShieldDNSReloadFiltersButton(coordinator, entry.entry_id),
            ShieldDNSClearLogsButton(coordinator, entry.entry_id),
            ShieldDNSRecheckUpstreamsButton(coordinator, entry.entry_id),
        ]
    )


class ShieldDNSRefreshListsButton(ShieldDNSEntity, ButtonEntity):
    """Representation of a ShieldDNS Refresh Lists button."""

    _attr_translation_key = "refresh_lists"
    _attr_icon = "mdi:sync"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_refresh_lists"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.client.refresh_blocklists()


class ShieldDNSReloadFiltersButton(ShieldDNSEntity, ButtonEntity):
    """Representation of a ShieldDNS Reload Filters button."""

    _attr_translation_key = "reload_filters"
    _attr_icon = "mdi:restart"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_reload_filters"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.client.full_reload()


class ShieldDNSClearLogsButton(ShieldDNSEntity, ButtonEntity):
    """Representation of a ShieldDNS Clear Logs button."""

    _attr_translation_key = "clear_logs"
    _attr_icon = "mdi:delete-sweep"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_clear_logs"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.client.clear_logs()


class ShieldDNSRecheckUpstreamsButton(ShieldDNSEntity, ButtonEntity):
    """Representation of a ShieldDNS Recheck Upstreams button."""

    _attr_translation_key = "recheck_upstreams"
    _attr_icon = "mdi:flask-round-bottom"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_recheck_upstreams"

    async def async_press(self) -> None:
        """Press the button."""
        await self.coordinator.client.recheck_upstreams()
