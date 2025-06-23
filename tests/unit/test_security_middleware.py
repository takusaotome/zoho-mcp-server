"""Unit tests for security middleware."""

from unittest.mock import Mock

import pytest
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from server.main import SecurityHeadersMiddleware, RequestSizeLimitMiddleware


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""

    @pytest.fixture
    def app(self):
        """Create mock FastAPI app."""
        return Mock()

    @pytest.fixture
    def middleware(self, app):
        """Create security headers middleware instance."""
        return SecurityHeadersMiddleware(app)

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        return request

    @pytest.mark.asyncio
    async def test_security_headers_added(self, middleware, mock_request):
        """Test that security headers are added to response."""
        # Mock call_next to return a basic response
        async def mock_call_next(req):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that security headers are present
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        
        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        
        assert "Permissions-Policy" in response.headers
        assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"

    @pytest.mark.asyncio
    async def test_csp_headers_development(self, middleware, mock_request, monkeypatch):
        """Test CSP headers in development mode."""
        # Mock settings directly in the middleware
        from server import main
        
        # Patch the settings import in the middleware module
        mock_settings = Mock()
        mock_settings.is_production = False
        monkeypatch.setattr(main, "settings", mock_settings)

        async def mock_call_next(req):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check CSP header for development
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "'unsafe-inline'" in csp
        assert "'unsafe-eval'" in csp
        assert "https://projectsapi.zoho.com" in csp

    @pytest.mark.asyncio
    async def test_csp_headers_production(self, middleware, mock_request, monkeypatch):
        """Test CSP headers in production mode."""
        # Mock settings directly in the middleware
        from server import main
        
        # Patch the settings import in the middleware module
        mock_settings = Mock()
        mock_settings.is_production = True
        monkeypatch.setattr(main, "settings", mock_settings)

        async def mock_call_next(req):
            response = Response(content="OK", status_code=200)
            return response

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check production-specific headers
        assert "Strict-Transport-Security" in response.headers
        assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
        
        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "https://projectsapi.zoho.com" in csp

    @pytest.mark.asyncio
    async def test_headers_preserved_on_json_response(self, middleware, mock_request):
        """Test that headers are added to JSON responses."""
        async def mock_call_next(req):
            return JSONResponse(content={"message": "success"}, status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that security headers are present on JSON response
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert isinstance(response, JSONResponse)


class TestRequestSizeLimitMiddleware:
    """Test request size limit middleware."""

    @pytest.fixture
    def app(self):
        """Create mock FastAPI app."""
        return Mock()

    @pytest.fixture
    def middleware(self, app):
        """Create request size limit middleware instance."""
        return RequestSizeLimitMiddleware(app, max_size=1024)  # 1KB for testing

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.headers = {}
        return request

    @pytest.mark.asyncio
    async def test_request_within_size_limit(self, middleware, mock_request):
        """Test request within size limit is allowed."""
        mock_request.headers = {"Content-Length": "512"}  # 512 bytes

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_exceeds_size_limit(self, middleware, mock_request):
        """Test request exceeding size limit is rejected."""
        mock_request.headers = {"Content-Length": "2048"}  # 2KB > 1KB limit

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 413
        assert isinstance(response, JSONResponse)
        
        # Check error message
        import json
        content = json.loads(response.body.decode())
        assert "Request Entity Too Large" in content["error"]
        assert "2048 bytes exceeds limit of 1024 bytes" in content["message"]

    @pytest.mark.asyncio
    async def test_request_no_content_length(self, middleware, mock_request):
        """Test request without Content-Length header is allowed."""
        # No Content-Length header
        mock_request.headers = {}

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_invalid_content_length(self, middleware, mock_request):
        """Test request with invalid Content-Length header."""
        mock_request.headers = {"Content-Length": "invalid"}

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 400
        assert isinstance(response, JSONResponse)
        
        # Check error message
        import json
        content = json.loads(response.body.decode())
        assert "Bad Request" in content["error"]
        assert "Invalid Content-Length header" in content["message"]

    @pytest.mark.asyncio
    async def test_middleware_initialization_with_custom_size(self, app):
        """Test middleware initialization with custom max size."""
        custom_size = 2048
        middleware = RequestSizeLimitMiddleware(app, max_size=custom_size)
        
        assert middleware.max_size == custom_size

    @pytest.mark.asyncio
    async def test_middleware_initialization_with_default_size(self, app):
        """Test middleware initialization with default max size."""
        middleware = RequestSizeLimitMiddleware(app)
        
        assert middleware.max_size == 1024 * 1024  # 1MB default

    @pytest.mark.asyncio
    async def test_request_at_exact_limit(self, middleware, mock_request):
        """Test request at exact size limit."""
        mock_request.headers = {"Content-Length": "1024"}  # Exactly at limit

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_one_byte_over_limit(self, middleware, mock_request):
        """Test request one byte over limit."""
        mock_request.headers = {"Content-Length": "1025"}  # 1 byte over limit

        async def mock_call_next(req):
            return Response(content="OK", status_code=200)

        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert response.status_code == 413