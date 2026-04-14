"""DataUpdateCoordinator for ShieldDNS."""

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

        init_kwargs = {
            "update_interval": timedelta(minutes=update_interval),
        }
        if "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters:
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
            stats = await self.client.get_stats()
            filtering_status = await self.client.get_filtering_status()
            clients = []
            try:
                clients = await self.client.get_clients()
            except ShieldDNSApiClientError:
                # Fallback for older versions that don't have /api/clients
                pass

            return {
                "stats": stats,
                "filtering_status": filtering_status,
                "clients": clients,
            }
        except ShieldDNSApiClientError as exception:
            raise UpdateFailed(
                f"Error communicating with API: {exception}"
            ) from exception
