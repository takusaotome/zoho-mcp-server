"""Tests for Zoho API client module."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from server.zoho.api_client import ZohoAPIClient, ZohoAPIError
from server.core.exceptions import ExternalAPIError, TemporaryError, TimeoutError


class TestZohoAPIError:
    """Test ZohoAPIError exception class."""

    def test_error_creation(self):
        """Test creating ZohoAPIError with all parameters."""
        error = ZohoAPIError("Test error", 400, {"error": "invalid_request"})
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.response_data == {"error": "invalid_request"}
        assert str(error) == "Test error"

    def test_error_creation_minimal(self):
        """Test creating ZohoAPIError with minimal parameters."""
        error = ZohoAPIError("Test error", 500)
        assert error.message == "Test error"
        assert error.status_code == 500
        assert error.response_data is None
        assert str(error) == "Test error"


class TestZohoAPIClient:
    """Test ZohoAPIClient class."""

    @pytest.fixture
    def client(self):
        """Create ZohoAPIClient instance."""
        return ZohoAPIClient()

    @pytest.fixture
    def mock_oauth_client(self):
        """Mock OAuth client."""
        with patch('server.zoho.api_client.oauth_client') as mock:
            mock.get_access_token = AsyncMock(return_value="test_access_token")
            yield mock

    def test_client_initialization(self, client):
        """Test ZohoAPIClient initialization."""
        assert client.projects_base_url is not None
        assert client.workdrive_base_url is not None
        assert client.timeout is not None
        assert client.max_retries == 3
        assert len(client.retry_delays) == 3
        assert client.retry_delays == [0.5, 1.0, 2.0]

    @pytest.mark.asyncio
    async def test_get_headers_projects(self, client, mock_oauth_client):
        """Test getting headers for Projects API."""
        headers = await client._get_headers(use_workdrive=False)

        mock_oauth_client.get_access_token.assert_called_once()
        assert headers["Authorization"] == "Zoho-oauthtoken test_access_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "zoho-mcp-server/0.1.0"

    @pytest.mark.asyncio
    async def test_get_headers_workdrive(self, client, mock_oauth_client):
        """Test getting headers for WorkDrive API."""
        headers = await client._get_headers(use_workdrive=True)

        mock_oauth_client.get_access_token.assert_called_once()
        assert headers["Authorization"] == "Zoho-oauthtoken test_access_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == "zoho-mcp-server/0.1.0"

    @pytest.mark.asyncio
    async def test_handle_response_success_with_json(self, client):
        """Test handling successful response with JSON."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://api.example.com/test"
        mock_response.json.return_value = {"status": "success", "data": {"id": 123}}

        with patch('server.zoho.api_client.logger'):
            result = await client._handle_response(mock_response, 0, 1)

        assert result == {"status": "success", "data": {"id": 123}}
        mock_response.json.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_response_success_empty(self, client):
        """Test handling successful response with empty body."""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.url = "https://api.example.com/test"
        mock_response.json.side_effect = Exception("No JSON")

        with patch('server.zoho.api_client.logger'):
            result = await client._handle_response(mock_response, 0, 1)

        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_response_rate_limit_with_retry(self, client):
        """Test handling rate limit with retry available."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}

        with patch('server.zoho.api_client.logger'), \
             patch('asyncio.sleep') as mock_sleep:

            with pytest.raises(Exception, match="Rate limited, retrying"):
                await client._handle_response(mock_response, 0, 2)  # attempt 0 of 2

        mock_sleep.assert_called_once_with(30)

    @pytest.mark.asyncio
    async def test_handle_response_rate_limit_final_attempt(self, client):
        """Test handling rate limit on final attempt."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.headers = {"Retry-After": "60"}

        with pytest.raises(ZohoAPIError) as exc_info:
            await client._handle_response(mock_response, 1, 2)  # final attempt

        assert exc_info.value.status_code == 429
        assert exc_info.value.message == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_handle_response_auth_error_with_retry(self, client, mock_oauth_client):
        """Test handling auth error with token refresh."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        # Reset the mock to ensure clean state
        mock_oauth_client.reset_mock()
        mock_oauth_client.get_access_token = AsyncMock()

        with patch('server.zoho.api_client.logger'):
            # The code actually raises ZohoAPIError after attempting token refresh
            with pytest.raises(ZohoAPIError, match="Authentication failed"):
                await client._handle_response(mock_response, 0, 2)

        mock_oauth_client.get_access_token.assert_called_once_with(force_refresh=True)

    @pytest.mark.asyncio
    async def test_handle_response_auth_error_final_attempt(self, client, mock_oauth_client):
        """Test handling auth error on final attempt."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with pytest.raises(ZohoAPIError) as exc_info:
            await client._handle_response(mock_response, 1, 2)

        assert exc_info.value.status_code == 401
        assert exc_info.value.message == "Authentication failed"

    @pytest.mark.asyncio
    async def test_handle_response_client_error_with_json(self, client):
        """Test handling client error with JSON response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid request", "code": "INVALID_DATA"}
        mock_response.text = "Bad Request"

        with patch('server.zoho.api_client.logger'):
            with pytest.raises(ZohoAPIError) as exc_info:
                await client._handle_response(mock_response, 0, 1)

        assert exc_info.value.status_code == 400
        assert "Invalid request" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_handle_response_client_error_no_json(self, client):
        """Test handling client error without JSON response."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.side_effect = Exception("No JSON")
        mock_response.text = "Not Found"

        with patch('server.zoho.api_client.logger'):
            with pytest.raises(ZohoAPIError) as exc_info:
                await client._handle_response(mock_response, 0, 1)

        assert exc_info.value.status_code == 404
        assert "Not Found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_handle_response_server_error_with_retry(self, client):
        """Test handling server error with retry available."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('server.zoho.api_client.logger'), \
             patch('asyncio.sleep') as mock_sleep:

            with pytest.raises(Exception, match="Server error 500, retrying"):
                await client._handle_response(mock_response, 0, 2)

        mock_sleep.assert_called_once_with(0.5)  # First retry delay

    @pytest.mark.asyncio
    async def test_handle_response_server_error_final_attempt(self, client):
        """Test handling server error on final attempt."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with pytest.raises(ZohoAPIError) as exc_info:
            await client._handle_response(mock_response, 1, 2)

        assert exc_info.value.status_code == 503
        assert "Server error: 503" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_handle_response_unexpected_status(self, client):
        """Test handling unexpected status code."""
        mock_response = Mock()
        mock_response.status_code = 999
        mock_response.url = "https://api.example.com/test"
        mock_response.text = "Unknown status"

        with patch('server.zoho.api_client.logger'):
            with pytest.raises(ZohoAPIError) as exc_info:
                await client._handle_response(mock_response, 0, 1)

        assert exc_info.value.status_code == 999
        # Status code 999 >= 500, so it's treated as a server error on final attempt
        assert "Server error: 999" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_make_request_success(self, client, mock_oauth_client):
        """Test successful make_request call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://api.example.com/test"
        mock_response.json.return_value = {"result": "success"}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                result = await client._make_request("GET", "/test", use_workdrive=False)

        assert result == {"result": "success"}
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert "/test" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_make_request_network_error_no_retry(self, client, mock_oauth_client):
        """Test make_request with network error and no retry."""
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                with pytest.raises(ExternalAPIError) as exc_info:
                    await client._make_request("GET", "/test", retry=False)

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_network_error_with_retry(self, client, mock_oauth_client):
        """Test make_request with network error and retry."""
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'), \
                 patch('asyncio.sleep') as mock_sleep:

                with pytest.raises(ExternalAPIError) as exc_info:
                    await client._make_request("GET", "/test", retry=True)

        # Should retry 3 times
        assert mock_client.request.call_count == 3
        assert mock_sleep.call_count == 2  # 2 retry delays
        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_method(self, client, mock_oauth_client):
        """Test GET method."""
        with patch.object(client, '_make_request', return_value={"data": "test"}) as mock_make_request:
            result = await client.get("/users", params={"limit": 10}, use_workdrive=True)

        mock_make_request.assert_called_once_with(
            "GET",
            "/users",
            use_workdrive=True,
            retry=True,
            params={"limit": 10}
        )
        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_post_method_with_json(self, client, mock_oauth_client):
        """Test POST method with JSON payload."""
        with patch.object(client, '_make_request', return_value={"id": 123}) as mock_make_request:
            result = await client.post(
                "/projects",
                json={"name": "Test Project"},
                use_workdrive=False,
                retry=False
            )

        mock_make_request.assert_called_once_with(
            "POST",
            "/projects",
            use_workdrive=False,
            retry=False,
            json={"name": "Test Project"}
        )
        assert result == {"id": 123}

    @pytest.mark.asyncio
    async def test_post_method_with_files(self, client, mock_oauth_client):
        """Test POST method with file upload."""
        files_data = {"file": ("test.txt", b"content", "text/plain")}

        with patch.object(client, '_make_request', return_value={"upload_id": "abc123"}) as mock_make_request:
            result = await client.post(
                "/upload",
                files=files_data,
                data={"name": "test"}
            )

        # Check that the call was made correctly (headers may or may not be included)
        mock_make_request.assert_called_once_with(
            "POST",
            "/upload",
            use_workdrive=False,
            retry=True,
            files=files_data,
            data={"name": "test"}
        )
        assert result == {"upload_id": "abc123"}

    @pytest.mark.asyncio
    async def test_put_method(self, client, mock_oauth_client):
        """Test PUT method."""
        with patch.object(client, '_make_request', return_value={"updated": True}) as mock_make_request:
            result = await client.put(
                "/projects/123",
                json={"name": "Updated Project"},
                use_workdrive=True
            )

        mock_make_request.assert_called_once_with(
            "PUT",
            "/projects/123",
            json={"name": "Updated Project"},
            headers=None,
            use_workdrive=True,
            retry=True
        )
        assert result == {"updated": True}

    @pytest.mark.asyncio
    async def test_delete_method(self, client, mock_oauth_client):
        """Test DELETE method."""
        with patch.object(client, '_make_request', return_value={}) as mock_make_request:
            result = await client.delete("/projects/123", retry=False)

        mock_make_request.assert_called_once_with(
            "DELETE",
            "/projects/123",
            use_workdrive=False,
            retry=False
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_oauth_client):
        """Test successful health check."""
        with patch.object(client, 'get', return_value={"user": {"id": "123"}}) as mock_get:
            result = await client.health_check()

        mock_get.assert_called_once_with("/user", retry=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, mock_oauth_client):
        """Test failed health check."""
        with patch.object(client, 'get', side_effect=ZohoAPIError("API Error", 500)) as mock_get, \
             patch('server.zoho.api_client.logger'):

            result = await client.health_check()

        mock_get.assert_called_once_with("/user", retry=False)
        assert result is False

    @pytest.mark.asyncio
    async def test_url_construction_projects(self, client, mock_oauth_client):
        """Test URL construction for Projects API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://projects.example.com/api/v3/test"
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                await client._make_request("GET", "/test", use_workdrive=False)

        call_args = mock_client.request.call_args
        assert client.projects_base_url.rstrip('/') in call_args[1]["url"]
        assert "/test" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_url_construction_workdrive(self, client, mock_oauth_client):
        """Test URL construction for WorkDrive API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://workdrive.example.com/api/v1/test"
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                await client._make_request("GET", "/test", use_workdrive=True)

        call_args = mock_client.request.call_args
        assert client.workdrive_base_url.rstrip('/') in call_args[1]["url"]
        assert "/test" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_header_merging(self, client, mock_oauth_client):
        """Test merging of custom headers with default headers."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://api.example.com/test"
        mock_response.json.return_value = {}

        custom_headers = {"X-Custom-Header": "test-value"}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                await client._make_request("GET", "/test", headers=custom_headers)

        call_args = mock_client.request.call_args
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Zoho-oauthtoken test_access_token"
        assert headers["X-Custom-Header"] == "test-value"

    @pytest.mark.asyncio
    async def test_async_context_manager(self, client):
        """Test async context manager functionality."""
        async with client as api_client:
            assert api_client is client
            # Verify that the client is properly initialized
            assert api_client._client is None  # Client is created on demand

    @pytest.mark.asyncio
    async def test_head_method(self, client, mock_oauth_client):
        """Test HEAD method."""
        with patch.object(client, '_make_request', return_value={"headers": "success"}) as mock_make_request:
            result = await client.head("/test")

        assert result == {"headers": "success"}
        mock_make_request.assert_called_once_with(
            "HEAD",
            "/test",
            headers=None,
            use_workdrive=False,
            retry=True
        )

    @pytest.mark.asyncio
    async def test_options_method(self, client, mock_oauth_client):
        """Test OPTIONS method."""
        with patch.object(client, '_make_request', return_value={"allowed_methods": ["GET", "POST"]}) as mock_make_request:
            result = await client.options("/test")

        assert result == {"allowed_methods": ["GET", "POST"]}
        mock_make_request.assert_called_once_with(
            "OPTIONS",
            "/test",
            headers=None,
            use_workdrive=False,
            retry=True
        )

    @pytest.mark.asyncio
    async def test_patch_method(self, client, mock_oauth_client):
        """Test PATCH method."""
        patch_data = {"name": "updated_name"}
        
        with patch.object(client, '_make_request', return_value={"updated": True}) as mock_make_request:
            result = await client.patch("/test", json=patch_data)

        assert result == {"updated": True}
        mock_make_request.assert_called_once_with(
            "PATCH",
            "/test",
            json=patch_data,
            headers=None,
            use_workdrive=False,
            retry=True
        )

    @pytest.mark.asyncio
    async def test_post_with_files_content_type_removal(self, client, mock_oauth_client):
        """Test POST method with files removes Content-Type header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://api.example.com/upload"
        mock_response.json.return_value = {"uploaded": True}

        files = {"file": ("test.txt", "test content", "text/plain")}

        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                result = await client.post("/upload", files=files)

        assert result == {"uploaded": True}
        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["files"] == files

    @pytest.mark.asyncio
    async def test_connection_pooling_client_reuse(self, client):
        """Test that HTTP client is reused for connection pooling."""
        # First call should create a new client
        client1 = await client._get_client()
        assert client1 is not None
        assert client._client is client1

        # Second call should reuse the same client
        client2 = await client._get_client()
        assert client2 is client1
        assert client._client is client1

    @pytest.mark.asyncio
    async def test_connection_pooling_client_recreation(self, client):
        """Test client recreation when closed."""
        # Create and close client
        client1 = await client._get_client()
        await client.close()

        # New call should create a new client
        client2 = await client._get_client()
        assert client2 is not client1
        assert client._client is client2

    @pytest.mark.asyncio
    async def test_handle_response_temporary_error_rate_limit(self, client):
        """Test handling rate limit with TemporaryError."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        mock_response.text = "Rate limit exceeded"

        with pytest.raises(TemporaryError) as exc_info:
            await client._handle_response(mock_response, 0, 2)  # Not final attempt

        assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_handle_response_auth_error_final_attempt(self, client, mock_oauth_client):
        """Test handling auth error on final attempt."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with pytest.raises(ZohoAPIError) as exc_info:
            await client._handle_response(mock_response, 1, 2)  # Final attempt

        assert exc_info.value.status_code == 401
        assert exc_info.value.message == "Authentication failed"

    @pytest.mark.asyncio
    async def test_handle_response_server_error_retry(self, client):
        """Test handling server error with retry logic."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch('asyncio.sleep') as mock_sleep:
            with pytest.raises(Exception, match="Server error 500, retrying"):
                await client._handle_response(mock_response, 0, 2)  # Not final attempt

        # Should sleep before retry
        mock_sleep.assert_called_once_with(0.5)  # First retry delay

    @pytest.mark.asyncio 
    async def test_head_method_exception_handling(self, client, mock_oauth_client):
        """Test HEAD method handles exceptions gracefully."""
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=Exception("Request failed"))
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                result = await client.head("/test")

        # Should return empty dict on exception
        assert result == {}

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, client, mock_oauth_client):
        """Test TimeoutError is raised properly."""
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
        
        with patch.object(client, '_get_client', return_value=mock_client):
            with patch('server.zoho.api_client.logger'):
                with pytest.raises(TimeoutError) as exc_info:
                    await client._make_request("GET", "/test", retry=False)

        assert "Request timed out" in str(exc_info.value)
        assert exc_info.value.timeout_duration == client.timeout.connect


def test_global_client_instance():
    """Test that a global client instance can be imported."""
    # This would typically test the global instance, but we don't have one in this module
    # Just test that we can create an instance
    client = ZohoAPIClient()
    assert isinstance(client, ZohoAPIClient)
