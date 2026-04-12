"""Binary sensor platform for ShieldDNS."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator
from .entity import ShieldDNSEntity


@dataclass(frozen=True, kw_only=True)
class ShieldDNSBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes ShieldDNS binary sensor entity."""

    is_on_fn: Callable[[dict[str, Any]], bool]
    required_version: str | None = None


BINARY_SENSORS: tuple[ShieldDNSBinarySensorEntityDescription, ...] = (
    ShieldDNSBinarySensorEntityDescription(
        key="abuse_protection_enabled",
        translation_key="abuse_protection_enabled",
        device_class=BinarySensorDeviceClass.PROTECTION,
        required_version="1.6.0",
        is_on_fn=lambda data: data.get("filtering_status", {}).get(
            "abuse_detection_enabled", False
        ),
    ),
    ShieldDNSBinarySensorEntityDescription(
        key="abuse_detected",
        translation_key="abuse_detected",
        device_class=BinarySensorDeviceClass.SAFETY,
        required_version="1.6.0",
        is_on_fn=lambda data: data.get("stats", {}).get("num_auto_blocked", 0) > 0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShieldDNS binary sensor based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ShieldDNSBinarySensor(coordinator, description, entry.entry_id)
        for description in BINARY_SENSORS
        if description.required_version is None
        or AwesomeVersion(coordinator.data.get("stats", {}).get("version", "0.0.0"))
        >= AwesomeVersion(description.required_version)
    )


class ShieldDNSBinarySensor(ShieldDNSEntity, BinarySensorEntity):
    """Representation of a ShieldDNS binary sensor."""

    entity_description: ShieldDNSBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        description: ShieldDNSBinarySensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(self.coordinator.data)
