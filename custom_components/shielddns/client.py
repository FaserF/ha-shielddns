"""API Client for ShieldDNS."""

import asyncio
import socket
from typing import Any

import aiohttp


class ShieldDNSApiClientError(Exception):
    """Exception to indicate a general API error."""


class ShieldDNSApiClientAuthenticationError(ShieldDNSApiClientError):
    """Exception to indicate an authentication error."""


class ShieldDNSApiClientCommunicationError(ShieldDNSApiClientError):
    """Exception to indicate a communication error."""


class ShieldDNSApiClient:
    """API Client for interacting with ShieldDNS."""

    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        session: aiohttp.ClientSession,
        use_ssl: bool = True,
        verify_ssl: bool = True,
    ) -> None:
        """Initialize."""
        self._host = host
        self._port = port
        self._token = token
        self._session = session
        self._use_ssl = use_ssl
        self._verify_ssl = verify_ssl

        schema = "https" if use_ssl else "http"
        self._base_url = f"{schema}://{host}:{port}/api"

    @property
    def use_ssl(self) -> bool:
        """Return whether SSL is used."""
        return self._use_ssl

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> Any:
        """Get information from the API."""
        if headers is None:
            headers = {}
        headers["Authorization"] = f"Bearer {self._token}"

        try:
            async with asyncio.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                    ssl=self._verify_ssl if self._use_ssl else False,
                )
                if response.status in (401, 403):
                    raise ShieldDNSApiClientAuthenticationError("Invalid credentials")
                response.raise_for_status()
                if "application/json" in response.headers.get("content-type", ""):
                    return await response.json()
                return await response.text()

        except TimeoutError as exception:
            raise ShieldDNSApiClientCommunicationError(
                "Timeout occurred"
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise ShieldDNSApiClientCommunicationError(
                f"Error communicating with API: {exception}"
            ) from exception

    async def get_stats(self) -> dict[str, Any]:
        """Get global stats."""
        return await self._api_wrapper("GET", f"{self._base_url}/stats")

    async def get_filtering_status(self) -> dict[str, Any]:
        """Get the current global filtering status."""
        return await self._api_wrapper("GET", f"{self._base_url}/filtering/status")

    async def toggle_filtering(self, enabled: bool) -> None:
        """Toggle global filtering on or off."""
        await self._api_wrapper(
            "POST", f"{self._base_url}/filtering/toggle", data={"enabled": enabled}
        )

    async def add_rule(self, domain: str, rule_type: str) -> None:
        """Add a domain to the block or allow list."""
        await self._api_wrapper(
            "POST",
            f"{self._base_url}/rules/add",
            data={"domain": domain, "type": rule_type},
        )

    async def remove_rule(self, domain: str) -> None:
        """Remove a domain from the block or allow list."""
        await self._api_wrapper(
            "POST", f"{self._base_url}/rules/remove", data={"domain": domain}
        )

    async def refresh_blocklists(self) -> None:
        """Trigger a blocklist refresh."""
        await self._api_wrapper("GET", f"{self._base_url}/refresh")
