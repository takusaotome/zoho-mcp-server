"""Tests for Redis client module."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from urllib.parse import urlparse

from server.storage.redis_client import RedisClient, redis_client


class TestRedisClient:
    """Test RedisClient class."""
    
    @pytest.fixture
    def client(self):
        """Create RedisClient instance."""
        return RedisClient()
    
    @pytest.fixture
    def mock_redis_client(self):
        """Create mock Redis client."""
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.set = AsyncMock()
        mock_client.setex = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.exists = AsyncMock()
        mock_client.ttl = AsyncMock()
        mock_client.expire = AsyncMock()
        mock_client.incr = AsyncMock()
        mock_client.hset = AsyncMock()
        mock_client.hget = AsyncMock()
        mock_client.hgetall = AsyncMock()
        mock_client.aclose = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool."""
        mock_pool = AsyncMock()
        mock_pool.disconnect = AsyncMock()
        return mock_pool
    
    def test_init(self, client):
        """Test RedisClient initialization."""
        assert client._pool is None
        assert client._client is None
        assert client._url is not None
        assert hasattr(client, '_password')
        assert hasattr(client, '_ssl')
    
    @pytest.mark.asyncio
    async def test_create_connection_success(self, client, mock_redis_client, mock_pool):
        """Test successful Redis connection creation."""
        with patch('server.storage.redis_client.ConnectionPool') as mock_pool_class, \
             patch('server.storage.redis_client.redis.Redis') as mock_redis_class:
            
            mock_pool_class.from_url.return_value = mock_pool
            mock_redis_class.return_value = mock_redis_client
            mock_redis_client.ping.return_value = True
            
            await client._create_connection()
            
            # Verify connection pool creation
            mock_pool_class.from_url.assert_called_once()
            assert client._pool == mock_pool
            
            # Verify Redis client creation
            mock_redis_class.assert_called_once_with(connection_pool=mock_pool)
            assert client._client == mock_redis_client
            
            # Verify ping test
            mock_redis_client.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_connection_failure(self, client):
        """Test Redis connection creation failure."""
        with patch('server.storage.redis_client.ConnectionPool') as mock_pool_class:
            mock_pool_class.from_url.side_effect = Exception("Connection failed")
            
            with pytest.raises(Exception, match="Connection failed"):
                await client._create_connection()
    
    @pytest.mark.asyncio
    async def test_ensure_connection_creates_new(self, client, mock_redis_client):
        """Test _ensure_connection creates new connection when none exists."""
        async def mock_create_connection():
            client._client = mock_redis_client
        
        with patch.object(client, '_create_connection', side_effect=mock_create_connection) as mock_create:
            client._client = None
            
            result = await client._ensure_connection()
            
            mock_create.assert_called_once()
            assert result == mock_redis_client
    
    @pytest.mark.asyncio
    async def test_ensure_connection_reuses_existing(self, client, mock_redis_client):
        """Test _ensure_connection reuses existing connection."""
        client._client = mock_redis_client
        
        with patch.object(client, '_create_connection') as mock_create:
            result = await client._ensure_connection()
            
            mock_create.assert_not_called()
            assert result == mock_redis_client
    
    @pytest.mark.asyncio
    async def test_get_success(self, client, mock_redis_client):
        """Test successful get operation."""
        mock_redis_client.get.return_value = b"test_value"
        client._client = mock_redis_client
        
        result = await client.get("test_key")
        
        mock_redis_client.get.assert_called_once_with("test_key")
        assert result == b"test_value"
    
    @pytest.mark.asyncio
    async def test_get_not_found(self, client, mock_redis_client):
        """Test get operation when key not found."""
        mock_redis_client.get.return_value = None
        client._client = mock_redis_client
        
        result = await client.get("nonexistent_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_failure(self, client, mock_redis_client):
        """Test get operation failure."""
        mock_redis_client.get.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.get("test_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_success(self, client, mock_redis_client):
        """Test successful set operation."""
        mock_redis_client.set.return_value = True
        client._client = mock_redis_client
        
        result = await client.set("test_key", "test_value", ex=300)
        
        mock_redis_client.set.assert_called_once_with("test_key", "test_value", ex=300)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_failure(self, client, mock_redis_client):
        """Test set operation failure."""
        mock_redis_client.set.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.set("test_key", "test_value")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_setex_success(self, client, mock_redis_client):
        """Test successful setex operation."""
        mock_redis_client.setex.return_value = True
        client._client = mock_redis_client
        
        result = await client.setex("test_key", 300, "test_value")
        
        mock_redis_client.setex.assert_called_once_with("test_key", 300, "test_value")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_setex_failure(self, client, mock_redis_client):
        """Test setex operation failure."""
        mock_redis_client.setex.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.setex("test_key", 300, "test_value")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_success(self, client, mock_redis_client):
        """Test successful delete operation."""
        mock_redis_client.delete.return_value = 2
        client._client = mock_redis_client
        
        result = await client.delete("key1", "key2")
        
        mock_redis_client.delete.assert_called_once_with("key1", "key2")
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_delete_failure(self, client, mock_redis_client):
        """Test delete operation failure."""
        mock_redis_client.delete.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.delete("key1", "key2")
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_exists_success(self, client, mock_redis_client):
        """Test successful exists operation."""
        mock_redis_client.exists.return_value = 2
        client._client = mock_redis_client
        
        result = await client.exists("key1", "key2")
        
        mock_redis_client.exists.assert_called_once_with("key1", "key2")
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_exists_failure(self, client, mock_redis_client):
        """Test exists operation failure."""
        mock_redis_client.exists.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.exists("key1", "key2")
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_ttl_success(self, client, mock_redis_client):
        """Test successful ttl operation."""
        mock_redis_client.ttl.return_value = 300
        client._client = mock_redis_client
        
        result = await client.ttl("test_key")
        
        mock_redis_client.ttl.assert_called_once_with("test_key")
        assert result == 300
    
    @pytest.mark.asyncio
    async def test_ttl_failure(self, client, mock_redis_client):
        """Test ttl operation failure."""
        mock_redis_client.ttl.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.ttl("test_key")
        
        assert result == -2
    
    @pytest.mark.asyncio
    async def test_expire_success(self, client, mock_redis_client):
        """Test successful expire operation."""
        mock_redis_client.expire.return_value = True
        client._client = mock_redis_client
        
        result = await client.expire("test_key", 300)
        
        mock_redis_client.expire.assert_called_once_with("test_key", 300)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_expire_failure(self, client, mock_redis_client):
        """Test expire operation failure."""
        mock_redis_client.expire.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.expire("test_key", 300)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_incr_success(self, client, mock_redis_client):
        """Test successful incr operation."""
        mock_redis_client.incr.return_value = 5
        client._client = mock_redis_client
        
        result = await client.incr("test_key", 2)
        
        mock_redis_client.incr.assert_called_once_with("test_key", 2)
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_incr_default_amount(self, client, mock_redis_client):
        """Test incr operation with default amount."""
        mock_redis_client.incr.return_value = 1
        client._client = mock_redis_client
        
        result = await client.incr("test_key")
        
        mock_redis_client.incr.assert_called_once_with("test_key", 1)
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_incr_failure(self, client, mock_redis_client):
        """Test incr operation failure."""
        mock_redis_client.incr.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.incr("test_key")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_hset_success(self, client, mock_redis_client):
        """Test successful hset operation."""
        mock_redis_client.hset.return_value = 2
        client._client = mock_redis_client
        
        mapping = {"field1": "value1", "field2": "value2"}
        result = await client.hset("test_hash", mapping)
        
        mock_redis_client.hset.assert_called_once_with("test_hash", mapping=mapping)
        assert result == 2
    
    @pytest.mark.asyncio
    async def test_hset_failure(self, client, mock_redis_client):
        """Test hset operation failure."""
        mock_redis_client.hset.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        mapping = {"field1": "value1"}
        result = await client.hset("test_hash", mapping)
        
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_hget_success(self, client, mock_redis_client):
        """Test successful hget operation."""
        mock_redis_client.hget.return_value = b"field_value"
        client._client = mock_redis_client
        
        result = await client.hget("test_hash", "field1")
        
        mock_redis_client.hget.assert_called_once_with("test_hash", "field1")
        assert result == b"field_value"
    
    @pytest.mark.asyncio
    async def test_hget_not_found(self, client, mock_redis_client):
        """Test hget operation when field not found."""
        mock_redis_client.hget.return_value = None
        client._client = mock_redis_client
        
        result = await client.hget("test_hash", "nonexistent_field")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_hget_failure(self, client, mock_redis_client):
        """Test hget operation failure."""
        mock_redis_client.hget.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.hget("test_hash", "field1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_hgetall_success(self, client, mock_redis_client):
        """Test successful hgetall operation."""
        expected_result = {b"field1": b"value1", b"field2": b"value2"}
        mock_redis_client.hgetall.return_value = expected_result
        client._client = mock_redis_client
        
        result = await client.hgetall("test_hash")
        
        mock_redis_client.hgetall.assert_called_once_with("test_hash")
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_hgetall_failure(self, client, mock_redis_client):
        """Test hgetall operation failure."""
        mock_redis_client.hgetall.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.hgetall("test_hash")
        
        assert result == {}
    
    @pytest.mark.asyncio
    async def test_ping_success(self, client, mock_redis_client):
        """Test successful ping operation."""
        mock_redis_client.ping.return_value = True
        client._client = mock_redis_client
        
        result = await client.ping()
        
        mock_redis_client.ping.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ping_failure(self, client, mock_redis_client):
        """Test ping operation failure."""
        mock_redis_client.ping.side_effect = Exception("Redis error")
        client._client = mock_redis_client
        
        result = await client.ping()
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close_with_client_and_pool(self, client, mock_redis_client, mock_pool):
        """Test close operation with both client and pool."""
        client._client = mock_redis_client
        client._pool = mock_pool
        
        await client.close()
        
        mock_redis_client.aclose.assert_called_once()
        mock_pool.disconnect.assert_called_once()
        assert client._client is None
        assert client._pool is None
    
    @pytest.mark.asyncio
    async def test_close_with_client_only(self, client, mock_redis_client):
        """Test close operation with client only."""
        client._client = mock_redis_client
        client._pool = None
        
        await client.close()
        
        mock_redis_client.aclose.assert_called_once()
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_close_with_pool_only(self, client, mock_pool):
        """Test close operation with pool only."""
        client._client = None
        client._pool = mock_pool
        
        await client.close()
        
        mock_pool.disconnect.assert_called_once()
        assert client._pool is None
    
    @pytest.mark.asyncio
    async def test_close_with_nothing(self, client):
        """Test close operation with no active connections."""
        client._client = None
        client._pool = None
        
        # Should not raise any exceptions
        await client.close()
        
        assert client._client is None
        assert client._pool is None
    
    @pytest.mark.asyncio
    async def test_connection_with_password_and_ssl(self, mock_redis_client, mock_pool):
        """Test connection creation with password and SSL enabled."""
        with patch('server.storage.redis_client.ConnectionPool') as mock_pool_class, \
             patch('server.storage.redis_client.redis.Redis') as mock_redis_class, \
             patch('server.storage.redis_client.settings') as mock_settings:
            
            # Configure settings for SSL and password
            mock_settings.redis_url = "rediss://localhost:6379/0"
            mock_settings.redis_password = "test_password"
            mock_settings.redis_ssl = True
            
            mock_pool_class.from_url.return_value = mock_pool
            mock_redis_class.return_value = mock_redis_client
            mock_redis_client.ping.return_value = True
            
            client = RedisClient()
            await client._create_connection()
            
            # Verify SSL and password configuration
            call_args = mock_pool_class.from_url.call_args
            assert call_args[1]['password'] == "test_password"
            assert call_args[1]['ssl'] is True
            assert call_args[1]['ssl_cert_reqs'] is None
    
    @pytest.mark.asyncio
    async def test_connection_without_password_and_ssl(self, mock_redis_client, mock_pool):
        """Test connection creation without password and SSL."""
        with patch('server.storage.redis_client.ConnectionPool') as mock_pool_class, \
             patch('server.storage.redis_client.redis.Redis') as mock_redis_class, \
             patch('server.storage.redis_client.settings') as mock_settings:
            
            # Configure settings without SSL and password
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_settings.redis_password = ""
            mock_settings.redis_ssl = False
            
            mock_pool_class.from_url.return_value = mock_pool
            mock_redis_class.return_value = mock_redis_client
            mock_redis_client.ping.return_value = True
            
            client = RedisClient()
            await client._create_connection()
            
            # Verify no SSL and no password configuration
            call_args = mock_pool_class.from_url.call_args
            assert call_args[1]['password'] is None
            assert call_args[1]['ssl'] is False
            assert call_args[1]['ssl_cert_reqs'] is None
    
    @pytest.mark.asyncio
    async def test_ensure_connection_in_all_methods(self, client, mock_redis_client):
        """Test that all methods properly ensure connection."""
        client._client = None
        
        with patch.object(client, '_ensure_connection', return_value=mock_redis_client) as mock_ensure:
            # Test various methods
            mock_redis_client.get.return_value = None
            await client.get("test")
            mock_ensure.assert_called()
            
            mock_ensure.reset_mock()
            mock_redis_client.set.return_value = True
            await client.set("test", "value")
            mock_ensure.assert_called()
            
            mock_ensure.reset_mock()
            mock_redis_client.ping.return_value = True
            await client.ping()
            mock_ensure.assert_called()


def test_global_redis_client_instance():
    """Test that global redis_client instance exists."""
    from server.storage.redis_client import redis_client
    assert isinstance(redis_client, RedisClient)