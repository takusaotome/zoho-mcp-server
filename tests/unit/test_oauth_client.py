"""Tests for Zoho OAuth client module."""

import asyncio
import httpx
import pytest
from unittest.mock import AsyncMock, Mock, patch

from server.zoho.oauth_client import ZohoOAuthClient, TokenResponse


class TestTokenResponse:
    """Test TokenResponse model."""
    
    def test_token_response_creation(self):
        """Test creating TokenResponse with all fields."""
        response = TokenResponse(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
            scope="ZohoProjects.projects.ALL",
            api_domain="https://projectsapi.zoho.com"
        )
        
        assert response.access_token == "test_token"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.scope == "ZohoProjects.projects.ALL"
        assert response.api_domain == "https://projectsapi.zoho.com"
    
    def test_token_response_defaults(self):
        """Test TokenResponse with default values."""
        response = TokenResponse(
            access_token="test_token",
            expires_in=3600,
            scope="ZohoProjects.projects.ALL",
            api_domain="https://projectsapi.zoho.com"
        )
        
        assert response.token_type == "Bearer"


class TestZohoOAuthClient:
    """Test ZohoOAuthClient class."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings with OAuth credentials."""
        with patch('server.zoho.oauth_client.settings') as mock:
            mock.zoho_client_id = "test_client_id"
            mock.zoho_client_secret = "test_client_secret"
            mock.zoho_refresh_token = "test_refresh_token"
            mock.token_cache_ttl_seconds = 3600
            yield mock
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('server.zoho.oauth_client.redis_client') as mock:
            mock.get = AsyncMock()
            mock.setex = AsyncMock()
            mock.delete = AsyncMock()
            mock.ttl = AsyncMock()
            yield mock
    
    @pytest.fixture
    def client(self, mock_settings, mock_redis):
        """Create ZohoOAuthClient instance."""
        return ZohoOAuthClient()
    
    def test_client_initialization(self, client):
        """Test ZohoOAuthClient initialization."""
        assert client.client_id == "test_client_id"
        assert client.client_secret == "test_client_secret"
        assert client.refresh_token == "test_refresh_token"
        assert client.token_url == "https://accounts.zoho.com/oauth/v2/token"
        assert client.cache_key == "zoho:access_token"
        assert client.cache_ttl == 3600
        assert client.max_retries == 3
        assert client.base_delay == 1.0
        assert client.max_delay == 60.0
    
    def test_validate_oauth_config_missing_client_id(self, mock_redis):
        """Test validation with missing client ID."""
        with patch('server.zoho.oauth_client.settings') as mock_settings:
            mock_settings.zoho_client_id = ""
            mock_settings.zoho_client_secret = "test_secret"
            mock_settings.zoho_refresh_token = "test_token"
            
            with pytest.raises(ValueError, match="ZOHO_CLIENT_ID is required"):
                ZohoOAuthClient()
    
    def test_validate_oauth_config_missing_client_secret(self, mock_redis):
        """Test validation with missing client secret."""
        with patch('server.zoho.oauth_client.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_id"
            mock_settings.zoho_client_secret = ""
            mock_settings.zoho_refresh_token = "test_token"
            
            with pytest.raises(ValueError, match="ZOHO_CLIENT_SECRET is required"):
                ZohoOAuthClient()
    
    def test_validate_oauth_config_missing_refresh_token(self, mock_redis):
        """Test validation with missing refresh token."""
        with patch('server.zoho.oauth_client.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_id"
            mock_settings.zoho_client_secret = "test_secret"
            mock_settings.zoho_refresh_token = ""
            
            with pytest.raises(ValueError, match="ZOHO_REFRESH_TOKEN is required"):
                ZohoOAuthClient()
    
    @pytest.mark.asyncio
    async def test_get_cached_token_success(self, client, mock_redis):
        """Test getting cached token successfully."""
        mock_redis.get.return_value = b"cached_token"
        
        with patch('server.zoho.oauth_client.logger'):
            result = await client._get_cached_token()
        
        mock_redis.get.assert_called_once_with("zoho:access_token")
        assert result == "cached_token"
    
    @pytest.mark.asyncio
    async def test_get_cached_token_string_response(self, client, mock_redis):
        """Test getting cached token when Redis returns string."""
        mock_redis.get.return_value = "cached_token"
        
        result = await client._get_cached_token()
        
        assert result == "cached_token"
    
    @pytest.mark.asyncio
    async def test_get_cached_token_not_found(self, client, mock_redis):
        """Test getting cached token when not found."""
        mock_redis.get.return_value = None
        
        result = await client._get_cached_token()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_cached_token_error(self, client, mock_redis):
        """Test getting cached token with Redis error."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        with patch('server.zoho.oauth_client.logger'):
            result = await client._get_cached_token()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, client, mock_redis):
        """Test getting access token from cache."""
        mock_redis.get.return_value = b"cached_token"
        
        with patch('server.zoho.oauth_client.logger'):
            result = await client.get_access_token()
        
        assert result == "cached_token"
        mock_redis.get.assert_called_once_with("zoho:access_token")
    
    @pytest.mark.asyncio
    async def test_get_access_token_force_refresh(self, client, mock_redis):
        """Test getting access token with forced refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ZohoProjects.projects.ALL",
            "api_domain": "https://projectsapi.zoho.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.get_access_token(force_refresh=True)
        
        assert result == "new_token"
        mock_redis.get.assert_not_called()  # Should not check cache when force_refresh=True
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, client, mock_redis):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ZohoProjects.projects.ALL",
            "api_domain": "https://projectsapi.zoho.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client._refresh_access_token()
        
        # Verify API call
        mock_client.post.assert_called_once_with(
            "https://accounts.zoho.com/oauth/v2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "refresh_token": "test_refresh_token",
            },
            timeout=30.0
        )
        
        # Verify caching
        mock_redis.setex.assert_called_once_with("zoho:access_token", 3300, "new_access_token")
        
        assert result == "new_access_token"
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_http_error(self, client, mock_redis):
        """Test token refresh with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.json.return_value = {
            "error": "invalid_grant",
            "error_description": "Invalid refresh token"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                with pytest.raises(Exception, match="Token refresh failed: 400 - invalid_grant"):
                    await client._refresh_access_token()
        
        # Should clear cached token on failure
        mock_redis.delete.assert_called_once_with("zoho:access_token")
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_network_error(self, client, mock_redis):
        """Test token refresh with network error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            with patch('server.zoho.oauth_client.logger'):
                with pytest.raises(Exception, match="Network error during token refresh"):
                    await client._refresh_access_token()
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_json_parse_error(self, client, mock_redis):
        """Test token refresh with JSON parsing error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                with pytest.raises(Exception, match="Token refresh failed: Invalid JSON"):
                    await client._refresh_access_token()
    
    @pytest.mark.asyncio
    async def test_cache_token_success(self, client, mock_redis):
        """Test successful token caching."""
        with patch('server.zoho.oauth_client.logger'):
            await client._cache_token("test_token", 3600)
        
        # Should cache for 3300 seconds (3600 - 300 buffer)
        mock_redis.setex.assert_called_once_with("zoho:access_token", 3300, "test_token")
    
    @pytest.mark.asyncio
    async def test_cache_token_ttl_limit(self, client, mock_redis):
        """Test token caching with TTL limit."""
        # client.cache_ttl is 3600, so it should use that as the limit
        with patch('server.zoho.oauth_client.logger'):
            await client._cache_token("test_token", 7200)  # 2 hours
        
        # Should use cache_ttl (3600) instead of expires_in - 300 (6900)
        mock_redis.setex.assert_called_once_with("zoho:access_token", 3600, "test_token")
    
    @pytest.mark.asyncio
    async def test_cache_token_error(self, client, mock_redis):
        """Test token caching with Redis error."""
        mock_redis.setex.side_effect = Exception("Redis error")
        
        with patch('server.zoho.oauth_client.logger'):
            # Should not raise exception, just log warning
            await client._cache_token("test_token", 3600)
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, client, mock_redis):
        """Test successful token revocation."""
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.revoke_token("test_token")
        
        mock_client.post.assert_called_once_with(
            "https://accounts.zoho.com/oauth/v2/token/revoke",
            data={"token": "test_token"},
            timeout=30.0
        )
        
        mock_redis.delete.assert_called_once_with("zoho:access_token")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, client, mock_redis):
        """Test token revocation failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.revoke_token("test_token")
        
        mock_redis.delete.assert_not_called()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_revoke_token_network_error(self, client, mock_redis):
        """Test token revocation with network error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.revoke_token("test_token")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_token_info_success(self, client):
        """Test successful token info retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 2400,
            "scope": "ZohoProjects.projects.ALL",
            "user_identifier": "test_user"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            result = await client.get_token_info("test_token")
        
        mock_client.post.assert_called_once_with(
            "https://accounts.zoho.com/oauth/v2/token/info",
            data={"access_token": "test_token"},
            timeout=30.0
        )
        
        assert result["access_token"] == "test_token"
        assert result["expires_in"] == 2400
    
    @pytest.mark.asyncio
    async def test_get_token_info_failure(self, client):
        """Test token info retrieval failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.get_token_info("test_token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_token_info_network_error(self, client):
        """Test token info retrieval with network error."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            
            with patch('server.zoho.oauth_client.logger'):
                result = await client.get_token_info("test_token")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_is_token_valid_true(self, client):
        """Test token validation when token is valid."""
        with patch.object(client, 'get_token_info', return_value={"valid": True}) as mock_get_info:
            result = await client.is_token_valid("test_token")
        
        mock_get_info.assert_called_once_with("test_token")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_token_valid_false(self, client):
        """Test token validation when token is invalid."""
        with patch.object(client, 'get_token_info', return_value=None) as mock_get_info:
            result = await client.is_token_valid("test_token")
        
        mock_get_info.assert_called_once_with("test_token")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_token_expiry_warning_no_cached_token(self, client, mock_redis):
        """Test expiry warning when no cached token."""
        mock_redis.get.return_value = None
        
        result = await client.get_token_expiry_warning()
        
        assert result == "No cached token found"
    
    @pytest.mark.asyncio
    async def test_get_token_expiry_warning_invalid_token(self, client, mock_redis):
        """Test expiry warning when token is invalid."""
        mock_redis.get.return_value = b"cached_token"
        
        with patch.object(client, 'get_token_info', return_value=None):
            result = await client.get_token_expiry_warning()
        
        assert result == "Token is invalid"
    
    @pytest.mark.asyncio
    async def test_get_token_expiry_warning_expires_soon(self, client, mock_redis):
        """Test expiry warning when token expires soon."""
        mock_redis.get.return_value = b"cached_token"
        mock_redis.ttl.return_value = 7200  # 2 hours
        
        with patch.object(client, 'get_token_info', return_value={"valid": True}):
            result = await client.get_token_expiry_warning()
        
        assert result == "Token expires in 2 hours"
    
    @pytest.mark.asyncio
    async def test_get_token_expiry_warning_not_expiring_soon(self, client, mock_redis):
        """Test expiry warning when token is not expiring soon."""
        mock_redis.get.return_value = b"cached_token"
        mock_redis.ttl.return_value = 86400 * 5  # 5 days
        
        with patch.object(client, 'get_token_info', return_value={"valid": True}):
            result = await client.get_token_expiry_warning()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_token_expiry_warning_error(self, client, mock_redis):
        """Test expiry warning with error in TTL check."""
        mock_redis.get.return_value = b"cached_token"
        mock_redis.ttl.side_effect = Exception("Redis TTL error")
        
        with patch.object(client, 'get_token_info', return_value={"valid": True}):
            with patch('server.zoho.oauth_client.logger'):
                result = await client.get_token_expiry_warning()
        
        assert "Token expiry check failed: Redis TTL error" in result

    @pytest.mark.asyncio
    async def test_refresh_access_token_rate_limit_retry(self, client, mock_redis):
        """Test token refresh with rate limiting and successful retry."""
        # First response: rate limited
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "2"}
        mock_response_429.json.return_value = {"error": "rate_limit_exceeded"}
        
        # Second response: success
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ZohoProjects.projects.ALL",
            "api_domain": "https://projectsapi.zoho.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])
            
            with patch('asyncio.sleep') as mock_sleep:
                with patch('server.zoho.oauth_client.logger'):
                    result = await client._refresh_access_token()
        
        # Should have made 2 calls
        assert mock_client.post.call_count == 2
        
        # Should have slept for the retry-after period
        mock_sleep.assert_called_once_with(2.0)
        
        # Verify successful result
        assert result == "new_access_token"
        mock_redis.setex.assert_called_once_with("zoho:access_token", 3300, "new_access_token")

    @pytest.mark.asyncio
    async def test_refresh_access_token_rate_limit_exponential_backoff(self, client, mock_redis):
        """Test token refresh with rate limiting using exponential backoff."""
        # Rate limited response without Retry-After header
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}
        mock_response_429.json.return_value = {"error": "rate_limit_exceeded"}
        
        # Success response
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ZohoProjects.projects.ALL",
            "api_domain": "https://projectsapi.zoho.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])
            
            with patch('asyncio.sleep') as mock_sleep:
                with patch('server.zoho.oauth_client.logger'):
                    result = await client._refresh_access_token()
        
        # Should use exponential backoff: base_delay * 2^0 = 1.0
        mock_sleep.assert_called_once_with(1.0)
        assert result == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_rate_limit_max_retries(self, client, mock_redis):
        """Test token refresh with rate limiting exceeding max retries."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {}
        mock_response_429.json.return_value = {"error": "rate_limit_exceeded"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response_429)
            
            with patch('asyncio.sleep') as mock_sleep:
                with patch('server.zoho.oauth_client.logger'):
                    with pytest.raises(Exception, match="Rate limit exceeded"):
                        await client._refresh_access_token()
        
        # Should have made 3 attempts (max_retries)
        assert mock_client.post.call_count == 3
        
        # Should have slept 2 times (between retries)
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff delays: 1.0, 2.0
        expected_delays = [1.0, 2.0]
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    @pytest.mark.asyncio
    async def test_refresh_access_token_server_error_retry(self, client, mock_redis):
        """Test token refresh with server error and retry."""
        # Server error response
        mock_response_500 = Mock()
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"
        mock_response_500.json.return_value = {"error": "server_error"}
        
        # Success response
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "ZohoProjects.projects.ALL",
            "api_domain": "https://projectsapi.zoho.com"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[mock_response_500, mock_response_200])
            
            with patch('asyncio.sleep') as mock_sleep:
                with patch('server.zoho.oauth_client.logger'):
                    result = await client._refresh_access_token()
        
        # Should use exponential backoff for server error
        mock_sleep.assert_called_once_with(1.0)
        assert result == "new_access_token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_non_retriable_error(self, client, mock_redis):
        """Test token refresh with non-retriable error."""
        mock_response_401 = Mock()
        mock_response_401.status_code = 401
        mock_response_401.text = "Unauthorized"
        mock_response_401.json.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client credentials"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response_401)
            
            with patch('server.zoho.oauth_client.logger'):
                with pytest.raises(Exception, match="Token refresh failed: 401 - invalid_client"):
                    await client._refresh_access_token()
        
        # Should only make one attempt for non-retriable errors
        assert mock_client.post.call_count == 1
        
        # Should clear cached token
        mock_redis.delete.assert_called_once_with("zoho:access_token")

    @pytest.mark.asyncio
    async def test_revoke_token_rate_limit_retry(self, client, mock_redis):
        """Test token revocation with rate limiting."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])
            
            with patch('asyncio.sleep') as mock_sleep:
                with patch('server.zoho.oauth_client.logger'):
                    result = await client.revoke_token("test_token")
        
        # Should retry and succeed
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once_with(1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_token_info_rate_limit_retry(self, client):
        """Test token info with rate limiting."""
        mock_response_429 = Mock()
        mock_response_429.status_code = 429
        
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"access_token": "test_token", "expires_in": 3600}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await client.get_token_info("test_token")
        
        # Should retry and succeed
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once_with(1.0)
        assert result["access_token"] == "test_token"


def test_global_oauth_client_instance():
    """Test that global oauth_client instance exists."""
    from server.zoho.oauth_client import oauth_client
    assert isinstance(oauth_client, ZohoOAuthClient)