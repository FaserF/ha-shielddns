"""Switch platform for ShieldDNS."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShieldDNS switch based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([ShieldDNSGlobalFilteringSwitch(coordinator, entry.entry_id)])


from .entity import ShieldDNSEntity


class ShieldDNSGlobalFilteringSwitch(ShieldDNSEntity, SwitchEntity):
    """Representation of a ShieldDNS Global Filtering switch."""

    _attr_translation_key = "global_filtering"
    _attr_icon = "mdi:shield-check"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_global_filtering"

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if not self.coordinator.data:
            return None
        status = self.coordinator.data.get("filtering_status", {})
        return status.get("enabled", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.coordinator.client.toggle_filtering(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        await self.coordinator.client.toggle_filtering(False)
        await self.coordinator.async_request_refresh()
