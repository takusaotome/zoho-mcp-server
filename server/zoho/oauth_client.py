"""Zoho OAuth client for token management."""

import logging
from datetime import datetime, timedelta, timezone
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
        
        logger.info("Zoho OAuth client initialized")
    
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
        """Refresh access token using refresh token.
        
        Returns:
            New access token
            
        Raises:
            Exception: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
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
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Token refresh failed: {response.status_code} - {error_detail}")
                    raise Exception(f"Token refresh failed: {response.status_code}")
                
                token_data = response.json()
                token_response = TokenResponse(**token_data)
                
                # Cache the new token
                await self._cache_token(token_response.access_token, token_response.expires_in)
                
                logger.info("Access token refreshed successfully")
                return token_response.access_token
                
        except httpx.RequestError as e:
            logger.error(f"Network error during token refresh: {e}")
            raise Exception(f"Network error during token refresh: {e}")
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            raise
    
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
        """Revoke an access token.
        
        Args:
            token: Access token to revoke
            
        Returns:
            True if revocation successful
        """
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
                else:
                    logger.warning(f"Token revocation failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.error(f"Token revocation error: {e}")
            return False
    
    async def get_token_info(self, token: str) -> Optional[dict]:
        """Get information about an access token.
        
        Args:
            token: Access token to check
            
        Returns:
            Token information or None if invalid
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://accounts.zoho.com/oauth/v2/token/info",
                    data={"access_token": token},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Token info request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Token info error: {e}")
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