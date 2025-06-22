"""Zoho OAuth client for token management."""

import asyncio
import logging
from typing import Optional

import httpx
from pydantic import BaseModel

from server.core.config import settings
from server.storage.redis_client import redis_client

logger = logging.getLogger(__name__)


class TokenResponse(BaseModel):
    """Zoho OAuth token response model."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    api_domain: str


class ZohoOAuthClient:
    """Zoho OAuth client for managing access tokens."""

    def __init__(self) -> None:
        """Initialize Zoho OAuth client."""
        self.client_id = settings.zoho_client_id
        self.client_secret = settings.zoho_client_secret
        self.refresh_token = settings.zoho_refresh_token
        self.token_url = "https://accounts.zoho.com/oauth/v2/token"
        self.cache_key = "zoho:access_token"
        self.cache_ttl = settings.token_cache_ttl_seconds

        # Rate limiting configuration
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds

        # Validate OAuth credentials
        self._validate_oauth_config()

        logger.info("Zoho OAuth client initialized")

    def _validate_oauth_config(self) -> None:
        """Validate OAuth configuration.

        Raises:
            ValueError: If required OAuth credentials are missing
        """
        if not self.client_id:
            raise ValueError("ZOHO_CLIENT_ID is required for OAuth authentication")
        if not self.client_secret:
            raise ValueError("ZOHO_CLIENT_SECRET is required for OAuth authentication")
        if not self.refresh_token:
            raise ValueError("ZOHO_REFRESH_TOKEN is required for OAuth authentication")

        logger.debug("OAuth configuration validated successfully")

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """Get valid access token, refreshing if necessary.

        Args:
            force_refresh: Force token refresh even if cached token exists

        Returns:
            Valid access token

        Raises:
            Exception: If token refresh fails
        """
        if not force_refresh:
            # Try to get cached token
            cached_token = await self._get_cached_token()
            if cached_token:
                logger.debug("Using cached access token")
                return cached_token

        # Refresh token
        logger.info("Refreshing Zoho access token")
        return await self._refresh_access_token()

    async def _get_cached_token(self) -> Optional[str]:
        """Get cached access token if valid.

        Returns:
            Cached token if valid, None otherwise
        """
        try:
            token_data = await redis_client.get(self.cache_key)
            if token_data:
                # Token exists in cache
                return token_data.decode('utf-8') if isinstance(token_data, bytes) else token_data
            return None
        except Exception as e:
            logger.warning(f"Failed to get cached token: {e}")
            return None

    async def _refresh_access_token(self) -> str:
        """Refresh access token using refresh token with rate limiting and retry logic.

        Returns:
            New access token

        Raises:
            Exception: If token refresh fails after all retries
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    logger.debug(f"Token refresh attempt {attempt + 1}/{self.max_retries}")

                    response = await client.post(
                        self.token_url,
                        data={
                            "grant_type": "refresh_token",
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                            "refresh_token": self.refresh_token,
                        },
                        timeout=30.0
                    )

                    token_data = response.json()

                    # Handle rate limiting (429 Too Many Requests)
                    if response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            # Get retry-after header or use exponential backoff
                            retry_after = int(response.headers.get("Retry-After", 0))
                            if retry_after > 0:
                                delay = min(retry_after, self.max_delay)
                            else:
                                delay = min(self.base_delay * (2 ** attempt), self.max_delay)

                            logger.warning(f"Rate limited (429), waiting {delay}s before retry {attempt + 2}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error("Rate limit exceeded, no more retries available")
                            raise Exception("Token refresh failed: 429 - Rate limit exceeded")

                    # Check for other errors in response
                    if response.status_code != 200 or "error" in token_data:
                        error_detail = token_data.get("error", response.text)
                        error_description = token_data.get("error_description", "Unknown error")

                        # For non-retriable errors, don't retry
                        if response.status_code in [400, 401, 403]:
                            logger.error(f"Token refresh failed with non-retriable error: {response.status_code} - {error_detail}: {error_description}")
                            await redis_client.delete(self.cache_key)
                            raise Exception(f"Token refresh failed: {response.status_code} - {error_detail}: {error_description}")

                        # For other server errors, retry with exponential backoff
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.warning(f"Token refresh failed ({response.status_code}), retrying in {delay}s: {error_detail}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(f"Token refresh failed after all retries: {response.status_code} - {error_detail}: {error_description}")
                            await redis_client.delete(self.cache_key)
                            raise Exception(f"Token refresh failed: {response.status_code} - {error_detail}: {error_description}")

                    # Success - parse and cache token
                    token_response = TokenResponse(**token_data)
                    await self._cache_token(token_response.access_token, token_response.expires_in)
                    logger.info("Access token refreshed successfully")
                    return token_response.access_token

            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Network error during token refresh, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Network error during token refresh after all retries: {e}")
                    raise Exception(f"Network error during token refresh: {e}")
            except Exception as e:
                if "Token refresh failed:" in str(e):
                    # Re-raise our custom exceptions without retry
                    raise

                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Unexpected error during token refresh, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Token refresh failed after all retries: {e}")
                    raise Exception(f"Token refresh failed: {e}")

        # This should never be reached, but just in case
        raise Exception("Token refresh failed: Maximum retries exceeded")

    async def _cache_token(self, access_token: str, expires_in: int) -> None:
        """Cache access token with expiration.

        Args:
            access_token: Access token to cache
            expires_in: Token expiration time in seconds
        """
        try:
            # Cache for slightly less time than actual expiration to be safe
            cache_ttl = min(expires_in - 300, self.cache_ttl)  # 5 minutes buffer

            await redis_client.setex(
                self.cache_key,
                cache_ttl,
                access_token
            )

            logger.debug(f"Token cached for {cache_ttl} seconds")
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")

    async def revoke_token(self, token: str) -> bool:
        """Revoke an access token with retry logic.

        Args:
            token: Access token to revoke

        Returns:
            True if revocation successful
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://accounts.zoho.com/oauth/v2/token/revoke",
                        data={"token": token},
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        # Remove from cache
                        await redis_client.delete(self.cache_key)
                        logger.info("Token revoked successfully")
                        return True
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.warning(f"Rate limited during revocation, waiting {delay}s")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.warning("Token revocation failed: Rate limit exceeded")
                            return False
                    else:
                        logger.warning(f"Token revocation failed: {response.status_code}")
                        return False

            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Token revocation error, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Token revocation error after all retries: {e}")
                    return False

        return False

    async def get_token_info(self, token: str) -> Optional[dict]:
        """Get information about an access token with retry logic.

        Args:
            token: Access token to check

        Returns:
            Token information or None if invalid
        """
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://accounts.zoho.com/oauth/v2/token/info",
                        data={"access_token": token},
                        timeout=30.0
                    )

                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                            logger.warning(f"Rate limited during token info check, waiting {delay}s")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.warning("Token info request failed: Rate limit exceeded")
                            return None
                    else:
                        logger.warning(f"Token info request failed: {response.status_code}")
                        return None

            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Token info error, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Token info error after all retries: {e}")
                    return None

        return None

    async def is_token_valid(self, token: str) -> bool:
        """Check if access token is valid.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid
        """
        token_info = await self.get_token_info(token)
        return token_info is not None

    async def get_token_expiry_warning(self) -> Optional[str]:
        """Get warning if token expires soon.

        Returns:
            Warning message if token expires within 3 days
        """
        try:
            cached_token = await self._get_cached_token()
            if not cached_token:
                return "No cached token found"

            token_info = await self.get_token_info(cached_token)
            if not token_info:
                return "Token is invalid"

            # Check if token expires within 3 days
            ttl = await redis_client.ttl(self.cache_key)
            if ttl < 3 * 24 * 3600:  # 3 days in seconds
                return f"Token expires in {ttl // 3600} hours"

            return None
        except Exception as e:
            logger.error(f"Token expiry check failed: {e}")
            return f"Token expiry check failed: {e}"


# Global OAuth client instance
oauth_client = ZohoOAuthClient()
