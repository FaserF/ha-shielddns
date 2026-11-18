"""Base entity for ShieldDNS."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator


class ShieldDNSEntity(CoordinatorEntity[ShieldDNSDataUpdateCoordinator]):
    """Base entity for ShieldDNS."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        entry_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self.entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        version = "Unknown"
        if self.coordinator.data and "stats" in self.coordinator.data:
            version = self.coordinator.data["stats"].get("version", "Unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry_id)},
            name=f"ShieldDNS ({self.coordinator.host})",
            manufacturer="ShieldDNS",
            model="Secure DNS Management",
            sw_version=version,
            configuration_url=self.coordinator.admin_url,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
