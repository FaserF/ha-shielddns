"""DataUpdateCoordinator for ShieldDNS."""

import asyncio
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ShieldDNSApiClient, ShieldDNSApiClientError
from .const import DOMAIN, LOGGER


class ShieldDNSDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching ShieldDNS data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: ShieldDNSApiClient,
        host: str,
        port: int,
        update_interval: int,
    ) -> None:
        """Initialize."""
        self.client = client
        self.host = host
        self.port = port
        # config_entry was added in Home Assistant 2024.12
        import inspect

        init_kwargs: dict[str, Any] = {
            "update_interval": timedelta(minutes=update_interval),
        }
        if (
            "config_entry"
            in inspect.signature(DataUpdateCoordinator.__init__).parameters
        ):
            init_kwargs["config_entry"] = config_entry

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            **init_kwargs,
        )

    @property
    def admin_url(self) -> str:
        """Return the admin URL."""
        protocol = "https" if self.client.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}/admin"

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via api client."""
        try:
            stats_task = self.client.get_stats()
            filtering_task = self.client.get_filtering_status()
            clients_task = self.client.get_clients()
            top_blocked_task = self.client.get_top_blocked()
            top_clients_task = self.client.get_top_clients()

            results = await asyncio.gather(
                stats_task,
                filtering_task,
                clients_task,
                top_blocked_task,
                top_clients_task,
                return_exceptions=True,
            )

            stats, filtering_status, clients, top_blocked, top_clients = results

            if isinstance(stats, Exception):
                raise stats
            if isinstance(filtering_status, Exception):
                raise filtering_status

            data = {
                "stats": stats,
                "filtering_status": filtering_status,
                "clients": clients
                if not isinstance(clients, Exception) and clients
                else [],
                "top_blocked": top_blocked
                if not isinstance(top_blocked, Exception) and top_blocked
                else [],
                "top_clients": top_clients
                if not isinstance(top_clients, Exception) and top_clients
                else [],
            }
            LOGGER.debug("ShieldDNS data update: %s", data)
            return data
        except ShieldDNSApiClientError as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception
