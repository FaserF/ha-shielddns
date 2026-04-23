"""Update platform for ShieldDNS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.components.update import (
    UpdateDeviceClass,
    UpdateEntity,
    UpdateEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator
from .entity import ShieldDNSEntity


@dataclass(frozen=True, kw_only=True)
class ShieldDNSUpdateEntityDescription(UpdateEntityDescription):
    """Describes ShieldDNS update entity."""

    installed_version_fn: Callable[[dict[str, Any]], str | None]
    latest_version_fn: Callable[[dict[str, Any]], str | None]


UPDATE_ENTITIES: tuple[ShieldDNSUpdateEntityDescription, ...] = (
    ShieldDNSUpdateEntityDescription(
        key="shielddns_update",
        translation_key="shielddns_update",
        device_class=UpdateDeviceClass.FIRMWARE,
        installed_version_fn=lambda data: (
            data.get("stats", {}).get("version")
            or data.get("stats", {}).get("Version")
            or None
        ),
        latest_version_fn=lambda data: (
            data.get("stats", {}).get("latest_version")
            or data.get("stats", {}).get("LatestVersion")
            or data.get("stats", {}).get("version")
            or data.get("stats", {}).get("Version")
            or None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShieldDNS update entity based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ShieldDNSUpdateEntity(coordinator, description, entry.entry_id)
        for description in UPDATE_ENTITIES
        if AwesomeVersion(coordinator.data.get("stats", {}).get("version", "0.0.0"))
        >= AwesomeVersion("1.6.0")
    )


class ShieldDNSUpdateEntity(ShieldDNSEntity, UpdateEntity):
    """Representation of a ShieldDNS update entity."""

    entity_description: ShieldDNSUpdateEntityDescription
    _attr_release_url = "https://github.com/FaserF/ShieldDNS/releases"

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        description: ShieldDNSUpdateEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def installed_version(self) -> str | None:
        """Return the installed version."""
        if not self.coordinator.data:
            return None
        return self.entity_description.installed_version_fn(self.coordinator.data)

    @property
    def latest_version(self) -> str | None:
        """Return the latest version."""
        if not self.coordinator.data:
            return None
        return self.entity_description.latest_version_fn(self.coordinator.data)
