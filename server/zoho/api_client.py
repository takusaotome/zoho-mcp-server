"""Zoho API client with retry logic and error handling."""

import asyncio
import logging
from typing import Any, Union, Optional

import httpx

from server.core.config import settings
from server.zoho.oauth_client import oauth_client

logger = logging.getLogger(__name__)


class ZohoAPIError(Exception):
    """Custom exception for Zoho API errors."""

    def __init__(self, message: str, status_code: int, response_data: Any = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class ZohoAPIClient:
    """HTTP client for Zoho APIs with authentication and retry logic."""

    def __init__(self) -> None:
        """Initialize Zoho API client."""
        self.projects_base_url = settings.api_base_url
        self.workdrive_base_url = settings.workdrive_api_url
        self.timeout = httpx.Timeout(30.0, connect=10.0)
        self.max_retries = 3
        self.retry_delays = [0.5, 1.0, 2.0]  # Exponential backoff

        logger.info("Zoho API client initialized")

    async def _get_headers(self, use_workdrive: bool = False) -> dict[str, str]:
        """Get request headers with authentication token.

        Args:
            use_workdrive: Whether this is for WorkDrive API

        Returns:
            Headers dictionary
        """
        access_token = await oauth_client.get_access_token()

        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "zoho-mcp-server/0.1.0"
        }

        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        use_workdrive: bool = False,
        retry: bool = False,
        **kwargs
    ) -> dict[str, Any]:
        """Make HTTP request to Zoho API with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            use_workdrive: Use WorkDrive base URL
            retry: Enable retry logic
            **kwargs: Additional request arguments

        Returns:
            API response data

        Raises:
            ZohoAPIError: If API request fails
        """
        base_url = self.workdrive_base_url if use_workdrive else self.projects_base_url
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = await self._get_headers(use_workdrive)

        # Merge headers with any provided headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        attempt = 0
        max_attempts = self.max_retries if retry else 1

        while attempt < max_attempts:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(f"Making {method} request to {url} (attempt {attempt + 1})")

                    response = await client.request(
                        method=method,
                        url=url,
                        headers=headers,
                        **kwargs
                    )

                    return await self._handle_response(response, attempt, max_attempts)

            except httpx.RequestError as e:
                attempt += 1
                if attempt >= max_attempts:
                    logger.error(f"Request failed after {max_attempts} attempts: {e}")
                    raise ZohoAPIError(f"Network error: {e}", 0)

                # Wait before retry
                await asyncio.sleep(self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)])
                logger.warning(f"Request failed, retrying ({attempt}/{max_attempts}): {e}")

    async def _handle_response(
        self,
        response: httpx.Response,
        attempt: int,
        max_attempts: int
    ) -> dict[str, Any]:
        """Handle API response and errors.

        Args:
            response: HTTP response
            attempt: Current attempt number
            max_attempts: Maximum attempts

        Returns:
            Parsed response data

        Raises:
            ZohoAPIError: If response indicates error
        """
        # Log response details
        logger.debug(f"Response: {response.status_code} {response.url}")

        # Handle success responses
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except Exception:
                # Some endpoints return empty responses
                return {}

        # Handle rate limiting
        if response.status_code == 429:
            if attempt < max_attempts - 1:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                raise Exception("Rate limited, retrying")
            else:
                raise ZohoAPIError("Rate limit exceeded", 429, response.text)

        # Handle authentication errors
        if response.status_code == 401:
            logger.warning("Authentication failed, attempting token refresh")
            try:
                # Force refresh token and retry once
                await oauth_client.get_access_token(force_refresh=True)
                if attempt < max_attempts - 1:
                    raise Exception("Authentication failed, retrying with new token")
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")

            raise ZohoAPIError("Authentication failed", 401, response.text)

        # Handle other client errors
        if 400 <= response.status_code < 500:
            try:
                error_data = response.json()
                error_message = error_data.get("message", response.text)
            except Exception:
                error_message = response.text

            logger.error(f"Client error {response.status_code}: {error_message}")
            raise ZohoAPIError(f"Client error: {error_message}", response.status_code, error_data if 'error_data' in locals() else None)

        # Handle server errors
        if response.status_code >= 500:
            if attempt < max_attempts - 1:
                # Retry on server errors
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                logger.warning(f"Server error {response.status_code}, retrying in {delay}s")
                await asyncio.sleep(delay)
                raise Exception(f"Server error {response.status_code}, retrying")
            else:
                raise ZohoAPIError(f"Server error: {response.status_code}", response.status_code, response.text)

        # Unexpected status code
        raise ZohoAPIError(f"Unexpected response: {response.status_code}", response.status_code, response.text)

    async def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        use_workdrive: bool = False,
        retry: bool = True
    ) -> dict[str, Any]:
        """Make GET request to Zoho API.

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            use_workdrive: Use WorkDrive API
            retry: Enable retry logic

        Returns:
            API response data
        """
        kwargs = {}
        if params:
            kwargs["params"] = params
        if headers:
            kwargs["headers"] = headers

        return await self._make_request(
            "GET",
            endpoint,
            use_workdrive=use_workdrive,
            retry=retry,
            **kwargs
        )

    async def post(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        use_workdrive: bool = False,
        retry: bool = True
    ) -> dict[str, Any]:
        """Make POST request to Zoho API.

        Args:
            endpoint: API endpoint
            json: JSON payload
            data: Form data
            files: Files to upload
            use_workdrive: Use WorkDrive API
            retry: Enable retry logic

        Returns:
            API response data
        """
        kwargs = {}
        headers = {}

        if files:
            # For file uploads, don't set Content-Type (let httpx handle it)
            headers.pop("Content-Type", None)
            kwargs["files"] = files

        if data:
            kwargs["data"] = data

        if json:
            kwargs["json"] = json

        if headers:
            kwargs["headers"] = headers

        return await self._make_request(
            "POST",
            endpoint,
            use_workdrive=use_workdrive,
            retry=retry,
            **kwargs
        )

    async def put(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        use_workdrive: bool = False,
        retry: bool = True
    ) -> dict[str, Any]:
        """Make PUT request to Zoho API.

        Args:
            endpoint: API endpoint
            json: JSON payload
            use_workdrive: Use WorkDrive API
            retry: Enable retry logic

        Returns:
            API response data
        """
        return await self._make_request(
            "PUT",
            endpoint,
            use_workdrive=use_workdrive,
            retry=retry,
            json=json
        )

    async def delete(
        self,
        endpoint: str,
        use_workdrive: bool = False,
        retry: bool = True
    ) -> dict[str, Any]:
        """Make DELETE request to Zoho API.

        Args:
            endpoint: API endpoint
            use_workdrive: Use WorkDrive API
            retry: Enable retry logic

        Returns:
            API response data
        """
        return await self._make_request(
            "DELETE",
            endpoint,
            use_workdrive=use_workdrive,
            retry=retry
        )

    async def health_check(self) -> bool:
        """Check if Zoho API is accessible.

        Returns:
            True if API is healthy
        """
        try:
            # Try to get user info as a health check
            response = await self.get("/user", retry=False)
            return response is not None
        except Exception as e:
            logger.error(f"Zoho API health check failed: {e}")
            return False
