"""Unit tests for authentication components."""

import ipaddress
from datetime import timezone, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from server.auth.ip_allowlist import IPAllowlistMiddleware
from server.auth.jwt_handler import JWTHandler, TokenData


class TestJWTHandler:
    """Test JWT authentication handler."""

    @pytest.fixture
    def jwt_handler(self):
        """Create JWT handler instance."""
        return JWTHandler()

    def test_create_access_token(self, jwt_handler):
        """Test access token creation."""
        token = jwt_handler.create_access_token("test_user")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self, jwt_handler):
        """Test valid token verification."""
        token = jwt_handler.create_access_token("test_user")
        token_data = jwt_handler.verify_token(token)

        assert isinstance(token_data, TokenData)
        assert token_data.sub == "test_user"
        assert token_data.exp > datetime.now(timezone.utc)

    def test_verify_invalid_token(self, jwt_handler):
        """Test invalid token verification."""
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token("invalid_token")

        assert exc_info.value.status_code == 401

    def test_verify_expired_token(self, jwt_handler):
        """Test expired token verification."""
        # Create token with immediate expiration
        token = jwt_handler.create_access_token(
            "test_user",
            expires_delta=timedelta(seconds=-1)
        )

        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(token)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_is_token_expired(self, jwt_handler):
        """Test token expiration check."""
        # Valid token
        valid_token = jwt_handler.create_access_token("test_user")
        assert not jwt_handler.is_token_expired(valid_token)

        # Expired token
        expired_token = jwt_handler.create_access_token(
            "test_user",
            expires_delta=timedelta(seconds=-1)
        )
        assert jwt_handler.is_token_expired(expired_token)

    def test_refresh_token_if_needed(self, jwt_handler):
        """Test token refresh logic."""
        # Token that doesn't need refresh
        token = jwt_handler.create_access_token("test_user")
        new_token = jwt_handler.refresh_token_if_needed(token, threshold_minutes=1)
        assert new_token is None

        # Token that needs refresh (expire soon)
        expiring_token = jwt_handler.create_access_token(
            "test_user",
            expires_delta=timedelta(minutes=1)
        )
        new_token = jwt_handler.refresh_token_if_needed(
            expiring_token,
            threshold_minutes=5
        )
        assert new_token is not None
        assert new_token != expiring_token


class TestIPAllowlistMiddleware:
    """Test IP allowlist middleware."""

    def test_parse_ip_list(self):
        """Test IP list parsing."""
        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.1", "10.0.0.0/8", "::1"]
        )

        assert len(middleware.allowed_networks) == 3
        assert any(isinstance(net, ipaddress.IPv4Network) for net in middleware.allowed_networks)
        assert any(isinstance(net, ipaddress.IPv6Network) for net in middleware.allowed_networks)

    def test_parse_invalid_ip(self):
        """Test invalid IP handling."""
        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.1", "invalid_ip", "10.0.0.0/8"]
        )

        # Should skip invalid IP and continue with valid ones
        assert len(middleware.allowed_networks) == 2

    def test_is_ip_allowed(self):
        """Test IP allowlist checking."""
        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.0/24", "10.0.0.1"]
        )

        # Test allowed IPs
        assert middleware._is_ip_allowed("192.168.1.100")
        assert middleware._is_ip_allowed("10.0.0.1")

        # Test blocked IPs
        assert not middleware._is_ip_allowed("192.168.2.1")
        assert not middleware._is_ip_allowed("172.16.0.1")

    def test_get_client_ip_direct(self):
        """Test direct client IP extraction."""
        request = Mock()
        request.headers = {}
        request.client.host = "192.168.1.100"

        middleware = IPAllowlistMiddleware(app=Mock(), allowed_ips=["192.168.1.0/24"])
        client_ip = middleware._get_client_ip(request)

        assert client_ip == "192.168.1.100"

    def test_get_client_ip_forwarded(self):
        """Test forwarded IP extraction."""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        request.client.host = "10.0.0.1"

        middleware = IPAllowlistMiddleware(app=Mock(), allowed_ips=["192.168.1.0/24"])
        client_ip = middleware._get_client_ip(request)

        assert client_ip == "192.168.1.100"

    def test_should_bypass_check(self):
        """Test bypass path checking."""
        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.0/24"],
            bypass_paths=["/health", "/docs"]
        )

        assert middleware._should_bypass_check("/health")
        assert middleware._should_bypass_check("/docs/swagger")
        assert not middleware._should_bypass_check("/api/tasks")

    @pytest.mark.asyncio
    async def test_dispatch_allowed_ip(self):
        """Test request dispatch with allowed IP."""
        request = Mock()
        request.url.path = "/api/tasks"
        request.headers = {}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock(return_value="success")

        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.0/24"]
        )

        response = await middleware.dispatch(request, call_next)

        assert response == "success"
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_blocked_ip(self):
        """Test request dispatch with blocked IP."""
        request = Mock()
        request.url.path = "/api/tasks"
        request.headers = {}
        request.client.host = "172.16.0.1"

        call_next = AsyncMock()

        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.0/24"]
        )

        response = await middleware.dispatch(request, call_next)

        assert response.status_code == 403
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_bypass_path(self):
        """Test request dispatch with bypass path."""
        request = Mock()
        request.url.path = "/health"
        request.headers = {}
        request.client.host = "172.16.0.1"  # Blocked IP

        call_next = AsyncMock(return_value="health_ok")

        middleware = IPAllowlistMiddleware(
            app=Mock(),
            allowed_ips=["192.168.1.0/24"]
        )

        response = await middleware.dispatch(request, call_next)

        assert response == "health_ok"
        call_next.assert_called_once_with(request)
