"""Unit tests for OAuth authentication handler."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from server.auth.oauth_handler import OAuthHandler


class TestOAuthHandler:
    """Test OAuth authentication handler."""

    @pytest.fixture
    def oauth_handler(self):
        """Create OAuth handler instance with test credentials."""
        with patch('server.auth.oauth_handler.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_client_id"
            mock_settings.zoho_client_secret = "test_client_secret"
            return OAuthHandler()

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_success(self, oauth_handler):
        """Test successful token exchange."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "scope": "ZohoProjects.tasks.ALL,ZohoProjects.projects.READ",
            "api_domain": "https://www.zohoapis.com"
        }
        mock_response.raise_for_status.return_value = None

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await oauth_handler.exchange_code_for_token("test_auth_code")

        # Verify result
        assert result["success"] is True
        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] == "test_refresh_token"
        assert result["expires_in"] == 3600
        assert result["scope"] == "ZohoProjects.tasks.ALL,ZohoProjects.projects.READ"
        assert result["api_domain"] == "https://www.zohoapis.com"

        # Verify API call
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            "https://accounts.zoho.com/oauth/v2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "redirect_uri": "http://localhost:8000/auth/callback",
                "code": "test_auth_code"
            }
        )

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_http_error(self, oauth_handler):
        """Test token exchange with HTTP error."""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"
        
        http_error = httpx.HTTPStatusError(
            "400 Bad Request",
            request=Mock(),
            response=mock_response
        )

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = http_error
            
            result = await oauth_handler.exchange_code_for_token("invalid_code")

        # Verify error result
        assert result["success"] is False
        assert "HTTP 400" in result["error"]
        assert "invalid_grant" in result["error"]

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_network_error(self, oauth_handler):
        """Test token exchange with network error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError("Network error")
            
            result = await oauth_handler.exchange_code_for_token("test_code")

        # Verify error result
        assert result["success"] is False
        assert "Network error" in result["error"]

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_invalid_json_response(self, oauth_handler):
        """Test token exchange with invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status.return_value = None

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await oauth_handler.exchange_code_for_token("test_code")

        # Verify error result
        assert result["success"] is False
        assert "Invalid JSON" in result["error"]

    def test_update_env_file_success(self, oauth_handler):
        """Test successful .env file update."""
        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as temp_file:
            temp_file.write("ZOHO_CLIENT_ID=test_id\n")
            temp_file.write("ZOHO_REFRESH_TOKEN=old_token\n")
            temp_file.write("OTHER_SETTING=value\n")
            temp_file_path = temp_file.name

        try:
            # Mock Path to point to our temporary file
            with patch('server.auth.oauth_handler.Path') as mock_path, \
                 patch('builtins.open', create=True) as mock_open, \
                 patch('os.environ') as mock_environ, \
                 patch('server.auth.oauth_handler.load_dotenv') as mock_load_dotenv, \
                 patch('server.auth.oauth_handler.settings') as mock_settings:
                
                # Setup Path mock
                mock_path.return_value.exists.return_value = True
                
                # Read the actual file content for testing
                with open(temp_file_path, 'r') as f:
                    original_content = f.readlines()
                
                # Mock open to return our test content
                mock_open.return_value.__enter__.return_value.readlines.return_value = original_content
                mock_open.return_value.__enter__.return_value.writelines = Mock()
                
                # Mock environment and settings
                mock_environ.clear = Mock()
                mock_settings.zoho_refresh_token = "old_token"

                # Execute the method
                result = oauth_handler.update_env_file("new_refresh_token")

                # Verify result
                assert result is True

                # Verify that file was written with updated content
                mock_open.return_value.__enter__.return_value.writelines.assert_called_once()
                written_lines = mock_open.return_value.__enter__.return_value.writelines.call_args[0][0]
                
                # Check that refresh token was updated
                token_line_found = False
                for line in written_lines:
                    if line.strip().startswith("ZOHO_REFRESH_TOKEN="):
                        assert "new_refresh_token" in line
                        token_line_found = True
                        break
                assert token_line_found

                # Verify settings update was attempted
                assert mock_settings.zoho_refresh_token == "new_refresh_token"

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    def test_update_env_file_add_new_token(self, oauth_handler):
        """Test adding refresh token to .env file when it doesn't exist."""
        original_content = [
            "ZOHO_CLIENT_ID=test_id\n",
            "OTHER_SETTING=value\n"
        ]

        with patch('server.auth.oauth_handler.Path') as mock_path, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.environ') as mock_environ, \
             patch('server.auth.oauth_handler.load_dotenv') as mock_load_dotenv, \
             patch('server.auth.oauth_handler.settings') as mock_settings:
            
            # Setup mocks
            mock_path.return_value.exists.return_value = True
            mock_open.return_value.__enter__.return_value.readlines.return_value = original_content
            mock_open.return_value.__enter__.return_value.writelines = Mock()
            mock_environ.clear = Mock()

            # Execute the method
            result = oauth_handler.update_env_file("new_token")

            # Verify result
            assert result is True

            # Verify that new token line was added
            written_lines = mock_open.return_value.__enter__.return_value.writelines.call_args[0][0]
            assert "ZOHO_REFRESH_TOKEN=new_token\n" in written_lines
            assert len(written_lines) == 3  # Original 2 lines + new token line

    def test_update_env_file_no_env_file(self, oauth_handler):
        """Test .env file update when file doesn't exist."""
        with patch('server.auth.oauth_handler.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            result = oauth_handler.update_env_file("new_token")

            # Verify failure
            assert result is False

    def test_update_env_file_read_error(self, oauth_handler):
        """Test .env file update with read error."""
        with patch('server.auth.oauth_handler.Path') as mock_path, \
             patch('builtins.open', side_effect=IOError("Permission denied")):
            
            mock_path.return_value.exists.return_value = True
            
            result = oauth_handler.update_env_file("new_token")

            # Verify failure
            assert result is False

    def test_update_env_file_write_error(self, oauth_handler):
        """Test .env file update with write error."""
        original_content = ["ZOHO_CLIENT_ID=test_id\n"]

        with patch('server.auth.oauth_handler.Path') as mock_path, \
             patch('builtins.open', create=True) as mock_open:
            
            mock_path.return_value.exists.return_value = True
            
            # Mock successful read but failed write
            mock_file = Mock()
            mock_file.readlines.return_value = original_content
            mock_file.writelines.side_effect = IOError("Disk full")
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = oauth_handler.update_env_file("new_token")

            # Verify failure
            assert result is False

    def test_update_env_file_settings_reload_error(self, oauth_handler):
        """Test .env file update when settings reload fails."""
        original_content = ["ZOHO_REFRESH_TOKEN=old_token\n"]

        with patch('server.auth.oauth_handler.Path') as mock_path, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.environ') as mock_environ, \
             patch('server.auth.oauth_handler.load_dotenv', side_effect=Exception("Import error")), \
             patch('server.auth.oauth_handler.settings') as mock_settings:
            
            # Setup successful file operations
            mock_path.return_value.exists.return_value = True
            mock_open.return_value.__enter__.return_value.readlines.return_value = original_content
            mock_open.return_value.__enter__.return_value.writelines = Mock()
            mock_environ.clear = Mock()

            # Execute the method (should succeed despite settings reload failure)
            result = oauth_handler.update_env_file("new_token")

            # Verify that file update succeeded even though settings reload failed
            assert result is True

    def test_oauth_handler_initialization(self):
        """Test OAuth handler initialization."""
        with patch('server.auth.oauth_handler.settings') as mock_settings:
            mock_settings.zoho_client_id = "test_client_id"
            mock_settings.zoho_client_secret = "test_client_secret"
            
            handler = OAuthHandler()

            assert handler.client_id == "test_client_id"
            assert handler.client_secret == "test_client_secret"
            assert handler.redirect_uri == "http://localhost:8000/auth/callback"

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_partial_response(self, oauth_handler):
        """Test token exchange with partial API response."""
        # Mock response with missing fields
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "expires_in": 3600
            # Missing refresh_token, scope, api_domain
        }
        mock_response.raise_for_status.return_value = None

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await oauth_handler.exchange_code_for_token("test_code")

        # Verify result handles missing fields gracefully
        assert result["success"] is True
        assert result["access_token"] == "test_access_token"
        assert result["refresh_token"] is None
        assert result["expires_in"] == 3600
        assert result["scope"] is None
        assert result["api_domain"] is None