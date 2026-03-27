"""Sensor platform for ShieldDNS."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator
from .entity import ShieldDNSEntity


@dataclass(frozen=True, kw_only=True)
class ShieldDNSSensorEntityDescription(SensorEntityDescription):
    """Describes ShieldDNS sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[ShieldDNSSensorEntityDescription, ...] = (
    ShieldDNSSensorEntityDescription(
        key="total_queries",
        translation_key="total_queries",
        icon="mdi:help-network",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.get("stats", {}).get("TotalQueries")
        or data.get("stats", {}).get("total_queries")
        or data.get("stats", {}).get("QueriesToday")
        or data.get("stats", {}).get("queries_today", 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="blocked_queries",
        translation_key="blocked_queries",
        icon="mdi:shield-alert",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: data.get("stats", {}).get("BlockedQueries")
        or data.get("stats", {}).get("blocked_queries")
        or data.get("stats", {}).get("BlockedToday")
        or data.get("stats", {}).get("blocked_today", 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="block_percentage",
        translation_key="block_percentage",
        icon="mdi:percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(
            (
                (data.get("stats", {}).get("BlockedQueries", 0) or data.get("stats", {}).get("blocked_queries", 0))
                / (data.get("stats", {}).get("TotalQueries", 1) or data.get("stats", {}).get("total_queries", 1))
                * 100
            ),
            1,
        ),
    ),
    ShieldDNSSensorEntityDescription(
        key="unique_clients",
        translation_key="unique_clients",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("stats", {}).get("UniqueClients")
        or data.get("stats", {}).get("unique_clients", 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="avg_response_time",
        translation_key="avg_response_time",
        icon="mdi:timer-outline",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(data.get("stats", {}).get("average_latency", 0.0), 2),
    ),
    ShieldDNSSensorEntityDescription(
        key="cache_hit_ratio",
        translation_key="cache_hit_ratio",
        icon="mdi:database-check",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(
            (
                data.get("stats", {}).get("cache_hits", 0)
                / (data.get("stats", {}).get("TotalQueries", 1) or data.get("stats", {}).get("total_queries", 1))
                * 100
            ),
            1,
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ShieldDNS sensor based on a config entry."""
    coordinator: ShieldDNSDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        ShieldDNSSensor(coordinator, description, entry.entry_id)
        for description in SENSORS
    )


class ShieldDNSSensor(ShieldDNSEntity, SensorEntity):
    """Representation of a ShieldDNS sensor."""

    entity_description: ShieldDNSSensorEntityDescription

    def __init__(
        self,
        coordinator: ShieldDNSDataUpdateCoordinator,
        description: ShieldDNSSensorEntityDescription,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
