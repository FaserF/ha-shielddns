"""Button platform for ShieldDNS."""

from homeassistant.components.button import ButtonEntity
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
    """Set up ShieldDNS button based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([ShieldDNSRefreshListsButton(coordinator, entry.entry_id)])


from .entity import ShieldDNSEntity


class ShieldDNSRefreshListsButton(ShieldDNSEntity, ButtonEntity):
    """Representation of a ShieldDNS Refresh Lists button."""

    _attr_translation_key = "refresh_lists"
    _attr_icon = "mdi:refresh"

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
