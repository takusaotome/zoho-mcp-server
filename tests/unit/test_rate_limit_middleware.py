"""Unit tests for rate limiting middleware."""

import time
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from server.middleware.rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""

    @pytest.fixture
    def app(self):
        """Create mock FastAPI app."""
        return Mock()

    @pytest.fixture
    def middleware(self, app):
        """Create rate limit middleware instance."""
        return RateLimitMiddleware(
            app=app,
            calls=5,  # 5 calls per period for testing
            period=60,  # 60 seconds
            bypass_paths=["/health", "/docs"]
        )

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {}
        request.client.host = "192.168.1.100"
        return request

    def test_middleware_initialization(self, app):
        """Test middleware initialization."""
        middleware = RateLimitMiddleware(
            app=app,
            calls=100,
            period=60,
            bypass_paths=["/health", "/metrics"]
        )

        assert middleware.calls == 100
        assert middleware.period == 60
        assert "/health" in middleware.bypass_paths
        assert "/metrics" in middleware.bypass_paths
        assert isinstance(middleware.clients, dict)

    def test_middleware_initialization_default_bypass_paths(self, app):
        """Test middleware initialization with default bypass paths."""
        middleware = RateLimitMiddleware(app=app)

        assert "/health" in middleware.bypass_paths
        assert "/docs" in middleware.bypass_paths
        assert "/openapi.json" in middleware.bypass_paths

    def test_get_client_identifier_from_ip(self, middleware, mock_request):
        """Test client identifier extraction from IP."""
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "192.168.1.100"

    def test_get_client_identifier_from_x_forwarded_for(self, middleware, mock_request):
        """Test client identifier extraction from X-Forwarded-For header."""
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.100"}
        mock_request.client.host = "192.168.1.100"

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "203.0.113.1"

    def test_get_client_identifier_from_x_real_ip(self, middleware, mock_request):
        """Test client identifier extraction from X-Real-IP header."""
        mock_request.headers = {"X-Real-IP": "203.0.113.2"}
        mock_request.client.host = "192.168.1.100"

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "203.0.113.2"

    def test_get_client_identifier_priority(self, middleware, mock_request):
        """Test header priority for client identification."""
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1",
            "X-Real-IP": "203.0.113.2"
        }
        mock_request.client.host = "192.168.1.100"

        # X-Forwarded-For should take priority
        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "203.0.113.1"

    def test_get_client_identifier_no_client(self, middleware):
        """Test client identifier when no client info available."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {}
        request.client = None

        client_id = middleware._get_client_identifier(mock_request)
        assert client_id == "unknown"

    def test_is_rate_limited_first_request(self, middleware, mock_request):
        """Test rate limiting for first request."""
        client_id = "192.168.1.100"
        
        is_limited = middleware._is_rate_limited(client_id)
        
        assert not is_limited
        assert client_id in middleware.clients
        assert middleware.clients[client_id]["count"] == 1

    def test_is_rate_limited_within_limit(self, middleware, mock_request):
        """Test rate limiting within allowed calls."""
        client_id = "192.168.1.100"
        
        # Make 4 requests (within limit of 5)
        for i in range(4):
            is_limited = middleware._is_rate_limited(client_id)
            assert not is_limited

        # Check final state
        assert middleware.clients[client_id]["count"] == 4

    def test_is_rate_limited_exceeded(self, middleware, mock_request):
        """Test rate limiting when limit is exceeded."""
        client_id = "192.168.1.100"
        
        # Make 5 requests (at limit)
        for i in range(5):
            is_limited = middleware._is_rate_limited(client_id)
            assert not is_limited

        # 6th request should be limited
        is_limited = middleware._is_rate_limited(client_id)
        assert is_limited

    def test_is_rate_limited_window_reset(self, middleware, mock_request):
        """Test rate limiting window reset."""
        client_id = "192.168.1.100"
        
        # Fill up the limit
        for i in range(5):
            middleware._is_rate_limited(client_id)

        # Simulate time passing beyond the window
        past_time = time.time() - middleware.period - 1
        middleware.clients[client_id]["window_start"] = past_time

        # Next request should reset the window
        is_limited = middleware._is_rate_limited(client_id)
        assert not is_limited
        assert middleware.clients[client_id]["count"] == 1

    def test_should_bypass_exact_path(self, middleware):
        """Test bypass for exact path match."""
        assert middleware._should_bypass(Mock(url=Mock(path="/health")))
        assert middleware._should_bypass(Mock(url=Mock(path="/docs")))

    def test_should_bypass_path_prefix(self, middleware):
        """Test bypass for path prefix match."""
        assert middleware._should_bypass(Mock(url=Mock(path="/docs/swagger")))
        assert middleware._should_bypass(Mock(url=Mock(path="/health/detailed")))

    def test_should_not_bypass_different_path(self, middleware):
        """Test no bypass for different path."""
        assert not middleware._should_bypass(Mock(url=Mock(path="/api/users")))
        assert not middleware._should_bypass(Mock(url=Mock(path="/test")))

    def test_cleanup_expired_entries(self, middleware):
        """Test cleanup of expired client entries."""
        # Add some client data
        current_time = time.time()
        expired_time = current_time - middleware.period - 1
        
        middleware.clients = {
            "active_client": {
                "count": 3,
                "window_start": current_time - 30  # Active within window
            },
            "expired_client": {
                "count": 5,
                "window_start": expired_time  # Expired
            },
            "another_expired": {
                "count": 2,
                "window_start": expired_time - 100  # Very expired
            }
        }

        middleware._cleanup_expired_entries()

        # Only active client should remain
        assert "active_client" in middleware.clients
        assert "expired_client" not in middleware.clients
        assert "another_expired" not in middleware.clients

    def test_add_rate_limit_headers_normal(self, middleware):
        """Test adding rate limit headers for normal response."""
        response = JSONResponse(content={"test": "data"})
        client_id = "192.168.1.100"
        
        # Make some requests to set up client data
        middleware._is_rate_limited(client_id)
        middleware._is_rate_limited(client_id)

        middleware._add_rate_limit_headers(response, client_id)

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "3"  # 5 - 2 = 3

    def test_add_rate_limit_headers_exceeded(self, middleware):
        """Test adding rate limit headers when limit exceeded."""
        response = JSONResponse(content={"test": "data"})
        client_id = "192.168.1.100"
        
        # Exceed the limit
        for i in range(6):
            middleware._is_rate_limited(client_id)

        middleware._add_rate_limit_headers(response, client_id)

        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "0"

    def test_add_rate_limit_headers_new_client(self, middleware):
        """Test adding rate limit headers for new client."""
        response = JSONResponse(content={"test": "data"})
        client_id = "new_client"

        middleware._add_rate_limit_headers(response, client_id)

        assert response.headers["X-RateLimit-Limit"] == "5"
        assert response.headers["X-RateLimit-Remaining"] == "5"  # No requests yet

    @pytest.mark.asyncio
    async def test_dispatch_allowed_request(self, middleware, mock_request):
        """Test dispatching allowed request."""
        call_next = AsyncMock(return_value=JSONResponse(content={"success": True}))

        response = await middleware.dispatch(mock_request, call_next)

        # Should call next middleware
        call_next.assert_called_once_with(mock_request)
        assert isinstance(response, JSONResponse)
        
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited_request(self, middleware, mock_request):
        """Test dispatching rate limited request."""
        client_id = middleware._get_client_identifier(mock_request)
        
        # Exceed rate limit
        for i in range(6):
            middleware._is_rate_limited(client_id)

        call_next = AsyncMock()

        response = await middleware.dispatch(mock_request, call_next)

        # Should not call next middleware
        call_next.assert_not_called()
        
        # Should return 429 response
        assert response.status_code == 429
        
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Remaining"] == "0"

    @pytest.mark.asyncio
    async def test_dispatch_bypass_path(self, middleware):
        """Test dispatching request for bypass path."""
        request = Mock(spec=Request)
        request.url.path = "/health"
        request.headers = {}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock(return_value=Response(content="OK"))

        # Even if client is rate limited, bypass paths should work
        client_id = middleware._get_client_identifier(mock_request)
        for i in range(6):
            middleware._is_rate_limited(client_id)

        response = await middleware.dispatch(mock_request, call_next)

        # Should call next middleware despite rate limit
        call_next.assert_called_once_with(request)
        assert response.content == b"OK"

    @pytest.mark.asyncio
    async def test_dispatch_periodic_cleanup(self, middleware, mock_request):
        """Test that periodic cleanup is triggered."""
        # Add expired entries
        expired_time = time.time() - middleware.period - 1
        middleware.clients["expired"] = {
            "count": 5,
            "window_start": expired_time
        }

        call_next = AsyncMock(return_value=Response())

        # Mock cleanup check to return True
        with Mock.patch.object(middleware, '_should_cleanup', return_value=True):
            await middleware.dispatch(mock_request, call_next)

        # Expired client should be removed
        assert "expired" not in middleware.clients

    @pytest.mark.asyncio
    async def test_dispatch_exception_handling(self, middleware, mock_request):
        """Test exception handling during dispatch."""
        call_next = AsyncMock(side_effect=Exception("Middleware error"))

        # Should not raise exception
        response = await middleware.dispatch(mock_request, call_next)

        # Should return 500 error response
        assert response.status_code == 500

    def test_should_cleanup_logic(self, middleware):
        """Test cleanup decision logic."""
        # Test with no requests
        assert not middleware._should_cleanup()

        # Add some clients and test cleanup intervals
        for i in range(15):
            middleware.clients[f"client_{i}"] = {
                "count": 1,
                "window_start": time.time()
            }

        # Should cleanup when there are many clients
        assert middleware._should_cleanup()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, middleware):
        """Test handling multiple concurrent requests from same client."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {}
        request.client.host = "192.168.1.100"

        call_next = AsyncMock(return_value=Response())

        # Simulate concurrent requests
        tasks = []
        for i in range(10):
            task = middleware.dispatch(request, call_next)
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, some should be rate limited
        success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)

        assert success_count > 0  # At least some should succeed
        assert rate_limited_count > 0  # Some should be rate limited
        assert success_count + rate_limited_count == 10