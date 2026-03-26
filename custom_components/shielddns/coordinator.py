"""DataUpdateCoordinator for ShieldDNS."""

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ShieldDNSApiClient, ShieldDNSApiClientError
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


class ShieldDNSDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching ShieldDNS data."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ShieldDNSApiClient,
        host: str,
        port: int,
    ) -> None:
        """Initialize."""
        self.client = client
        self.host = host
        self.port = port
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    @property
    def admin_url(self) -> str:
        """Return the admin URL."""
        protocol = "https" if self.client._use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}/admin"

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via api client."""
        try:
            stats = await self.client.get_stats()
            filtering_status = await self.client.get_filtering_status()
            return {
                "stats": stats,
                "filtering_status": filtering_status,
            }
        except ShieldDNSApiClientError as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception
