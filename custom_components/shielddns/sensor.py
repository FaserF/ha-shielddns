"""Sensor platform for ShieldDNS."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from awesomeversion import AwesomeVersion
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ShieldDNSDataUpdateCoordinator
from .entity import ShieldDNSEntity


@dataclass(frozen=True, kw_only=True)
class ShieldDNSSensorEntityDescription(SensorEntityDescription):
    """Describes ShieldDNS sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    required_version: str | None = None


def _get_stat(data: dict[str, Any], keys: list[str], default: Any = 0) -> Any:
    """Extract a statistic from data using multiple possible keys."""
    stats = data.get("stats", {})
    for key in keys:
        if (value := stats.get(key)) is not None:
            return value
    return default


SENSORS: tuple[ShieldDNSSensorEntityDescription, ...] = (
    ShieldDNSSensorEntityDescription(
        key="total_queries",
        translation_key="total_queries",
        icon="mdi:help-network",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: _get_stat(
            data, ["TotalQueries", "total_queries", "QueriesToday", "queries_today"]
        ),
    ),
    ShieldDNSSensorEntityDescription(
        key="blocked_queries",
        translation_key="blocked_queries",
        icon="mdi:shield-alert",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda data: _get_stat(
            data, ["BlockedQueries", "blocked_queries", "BlockedToday", "blocked_today"]
        ),
    ),
    ShieldDNSSensorEntityDescription(
        key="block_percentage",
        translation_key="block_percentage",
        icon="mdi:percent",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(
            (
                _get_stat(
                    data,
                    [
                        "BlockedQueries",
                        "blocked_queries",
                        "BlockedToday",
                        "blocked_today",
                    ],
                )
                / max(
                    _get_stat(
                        data,
                        [
                            "TotalQueries",
                            "total_queries",
                            "QueriesToday",
                            "queries_today",
                        ],
                    ),
                    1,
                )
                * 100
            ),
            0,
        ),
    ),
    ShieldDNSSensorEntityDescription(
        key="unique_clients",
        translation_key="unique_clients",
        icon="mdi:lan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _get_stat(data, ["UniqueClients", "unique_clients"]),
    ),
    ShieldDNSSensorEntityDescription(
        key="avg_response_time",
        translation_key="avg_response_time",
        icon="mdi:timer-outline",
        native_unit_of_measurement="ms",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(_get_stat(data, ["average_latency"], 0.0), 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="cache_hit_ratio",
        translation_key="cache_hit_ratio",
        icon="mdi:database-check",
        native_unit_of_measurement="%",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: round(
            (
                _get_stat(data, ["cache_hits", "CacheHits"])
                / max(
                    _get_stat(
                        data,
                        [
                            "TotalQueries",
                            "total_queries",
                            "QueriesToday",
                            "queries_today",
                        ],
                    ),
                    1,
                )
                * 100
            ),
            0,
        ),
    ),
    ShieldDNSSensorEntityDescription(
        key="db_size",
        translation_key="db_size",
        icon="mdi:database",
        native_unit_of_measurement="MB",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        required_version="1.6.0",
        value_fn=lambda data: round(_get_stat(data, ["db_size_mb"], 0.0), 2),
    ),
    ShieldDNSSensorEntityDescription(
        key="ram_usage",
        translation_key="ram_usage",
        icon="mdi:memory",
        native_unit_of_measurement="MB",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        required_version="1.6.0",
        value_fn=lambda data: round(_get_stat(data, ["ram_used_mb"], 0.0), 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        icon="mdi:cpu-64-bit",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        required_version="1.6.0",
        value_fn=lambda data: round(_get_stat(data, ["cpu_usage"], 0.0), 2),
    ),
    ShieldDNSSensorEntityDescription(
        key="auto_blocked_count",
        translation_key="auto_blocked_count",
        icon="mdi:account-lock",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        required_version="1.6.0",
        value_fn=lambda data: _get_stat(data, ["num_auto_blocked"], 0),
    ),
    ShieldDNSSensorEntityDescription(
        key="connected_clients",
        translation_key="connected_clients",
        icon="mdi:account-group",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        required_version="1.6.0",
        value_fn=lambda data: len(data.get("clients", [])),
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
        if description.required_version is None
        or AwesomeVersion(coordinator.data.get("stats", {}).get("version", "0.0.0"))
        >= AwesomeVersion(description.required_version)
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
