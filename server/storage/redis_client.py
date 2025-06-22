"""Redis client for caching and storage."""

import logging
from typing import Dict, Optional, Union
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from server.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with connection management."""

    def __init__(self) -> None:
        """Initialize Redis client."""
        self._pool: Optional[ConnectionPool] = None
        self._client: redis.Optional[Redis] = None
        self._url = settings.redis_url
        self._password = settings.redis_password
        self._ssl = settings.redis_ssl

    async def _ensure_connection(self) -> redis.Redis:
        """Ensure Redis connection is established.

        Returns:
            Redis client instance
        """
        if self._client is None:
            await self._create_connection()
        if self._client is None:
            raise RuntimeError("Failed to establish Redis connection")
        return self._client

    async def _create_connection(self) -> None:
        """Create Redis connection pool and client."""
        try:
            # Parse Redis URL
            parsed_url = urlparse(self._url)

            # Create connection pool
            pool_kwargs = {
                "password": self._password if self._password else None,
                "decode_responses": False,  # Handle encoding manually
                "max_connections": 20,
                "retry_on_timeout": True,
                "socket_timeout": 5,
                "socket_connect_timeout": 5
            }

            # Add SSL settings only if SSL is enabled
            if self._ssl:
                pool_kwargs["ssl"] = True
                pool_kwargs["ssl_cert_reqs"] = None

            self._pool = ConnectionPool.from_url(self._url, **pool_kwargs)

            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            logger.info(f"Redis connected to {parsed_url.hostname}:{parsed_url.port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def get(self, key: str) -> Optional[bytes]:
        """Get value by key.

        Args:
            key: Redis key

        Returns:
            Value as bytes or None if not found
        """
        try:
            client = await self._ensure_connection()
            result = await client.get(key)
            return result if result is None else bytes(result)
        except Exception as e:
            logger.error(f"Redis GET failed for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Union[str, bytes],
        ex: Optional[int] = None
    ) -> bool:
        """Set key-value pair.

        Args:
            key: Redis key
            value: Value to store
            ex: Expiration time in seconds

        Returns:
            True if successful
        """
        try:
            client = await self._ensure_connection()
            result = await client.set(key, value, ex=ex)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET failed for key '{key}': {e}")
            return False

    async def setex(self, key: str, time: int, value: Union[str, bytes]) -> bool:
        """Set key-value pair with expiration.

        Args:
            key: Redis key
            time: Expiration time in seconds
            value: Value to store

        Returns:
            True if successful
        """
        try:
            client = await self._ensure_connection()
            result = await client.setex(key, time, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SETEX failed for key '{key}': {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """Delete keys.

        Args:
            keys: Keys to delete

        Returns:
            Number of keys deleted
        """
        try:
            client = await self._ensure_connection()
            result = await client.delete(*keys)
            return int(result)
        except Exception as e:
            logger.error(f"Redis DELETE failed for keys {keys}: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Check if keys exist.

        Args:
            keys: Keys to check

        Returns:
            Number of existing keys
        """
        try:
            client = await self._ensure_connection()
            result = await client.exists(*keys)
            return int(result)
        except Exception as e:
            logger.error(f"Redis EXISTS failed for keys {keys}: {e}")
            return 0

    async def ttl(self, key: str) -> int:
        """Get time to live for key.

        Args:
            key: Redis key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            client = await self._ensure_connection()
            result = await client.ttl(key)
            return int(result)
        except Exception as e:
            logger.error(f"Redis TTL failed for key '{key}': {e}")
            return -2

    async def expire(self, key: str, time: int) -> bool:
        """Set expiration for key.

        Args:
            key: Redis key
            time: Expiration time in seconds

        Returns:
            True if successful
        """
        try:
            client = await self._ensure_connection()
            result = await client.expire(key, time)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key '{key}': {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment key value.

        Args:
            key: Redis key
            amount: Increment amount

        Returns:
            New value or None if failed
        """
        try:
            client = await self._ensure_connection()
            result = await client.incr(key, amount)
            return int(result)
        except Exception as e:
            logger.error(f"Redis INCR failed for key '{key}': {e}")
            return None

    async def hset(
        self,
        name: str,
        mapping: Dict[str, Union[str, bytes]]
    ) -> int:
        """Set hash fields.

        Args:
            name: Hash name
            mapping: Field-value mapping

        Returns:
            Number of fields added
        """
        try:
            client = await self._ensure_connection()
            result = await client.hset(name, mapping=mapping)
            return int(result)
        except Exception as e:
            logger.error(f"Redis HSET failed for hash '{name}': {e}")
            return 0

    async def hget(self, name: str, key: str) -> Optional[bytes]:
        """Get hash field value.

        Args:
            name: Hash name
            key: Field name

        Returns:
            Field value or None if not found
        """
        try:
            client = await self._ensure_connection()
            result = await client.hget(name, key)
            return bytes(result) if result is not None else None
        except Exception as e:
            logger.error(f"Redis HGET failed for hash '{name}', field '{key}': {e}")
            return None

    async def hgetall(self, name: str) -> dict[bytes, bytes]:
        """Get all hash fields and values.

        Args:
            name: Hash name

        Returns:
            Dictionary of field-value pairs
        """
        try:
            client = await self._ensure_connection()
            result = await client.hgetall(name)
            return {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in result.items()}
        except Exception as e:
            logger.error(f"Redis HGETALL failed for hash '{name}': {e}")
            return {}

    async def ping(self) -> bool:
        """Ping Redis server.

        Returns:
            True if ping successful
        """
        try:
            client = await self._ensure_connection()
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis PING failed: {e}")
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        logger.info("Redis connection closed")


# Global Redis client instance
redis_client = RedisClient()
