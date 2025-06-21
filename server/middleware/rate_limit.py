"""Rate limiting middleware for Zoho MCP Server."""

import logging
import time
from typing import Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to implement rate limiting per client IP."""
    
    def __init__(
        self,
        app,
        calls: int = 100,
        period: int = 60,
        bypass_paths: Optional[list[str]] = None
    ) -> None:
        """Initialize rate limiting middleware.
        
        Args:
            app: FastAPI application
            calls: Number of calls allowed per period
            period: Time period in seconds
            bypass_paths: List of paths that bypass rate limiting
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.bypass_paths = bypass_paths or ["/health", "/docs", "/openapi.json"]
        
        # In-memory storage for rate limiting (use Redis in production)
        self.clients: Dict[str, Dict[str, float]] = {}
        
        logger.info(f"Rate limiting initialized: {calls} calls per {period} seconds")
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get client identifier for rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client identifier (IP address)
        """
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                client_ip = real_ip.strip()
            else:
                client_ip = request.client.host if request.client else "unknown"
        
        return client_ip
    
    def _should_bypass_check(self, path: str) -> bool:
        """Check if path should bypass rate limiting.
        
        Args:
            path: Request path
            
        Returns:
            True if should bypass check
        """
        return any(path.startswith(bypass_path) for bypass_path in self.bypass_paths)
    
    def _cleanup_expired_entries(self, current_time: float) -> None:
        """Clean up expired entries from client tracking.
        
        Args:
            current_time: Current timestamp
        """
        expired_clients = []
        
        for client_id, client_data in self.clients.items():
            # Remove entries older than the period
            client_data["requests"] = [
                req_time for req_time in client_data["requests"]
                if current_time - req_time < self.period
            ]
            
            # Mark client for removal if no recent requests
            if not client_data["requests"]:
                expired_clients.append(client_id)
        
        # Remove expired clients
        for client_id in expired_clients:
            del self.clients[client_id]
    
    def _is_rate_limited(self, client_id: str) -> tuple[bool, int, float]:
        """Check if client is rate limited.
        
        Args:
            client_id: Client identifier
            
        Returns:
            Tuple of (is_limited, remaining_calls, reset_time)
        """
        current_time = time.time()
        
        # Clean up expired entries periodically
        if len(self.clients) > 1000:  # Cleanup threshold
            self._cleanup_expired_entries(current_time)
        
        # Initialize client data if not exists
        if client_id not in self.clients:
            self.clients[client_id] = {
                "requests": [],
                "first_request": current_time
            }
        
        client_data = self.clients[client_id]
        
        # Remove requests older than the period
        client_data["requests"] = [
            req_time for req_time in client_data["requests"]
            if current_time - req_time < self.period
        ]
        
        # Check if rate limit exceeded
        if len(client_data["requests"]) >= self.calls:
            oldest_request = min(client_data["requests"])
            reset_time = oldest_request + self.period
            return True, 0, reset_time
        
        # Add current request
        client_data["requests"].append(current_time)
        
        # Calculate remaining calls and reset time
        remaining_calls = self.calls - len(client_data["requests"])
        oldest_request = min(client_data["requests"]) if client_data["requests"] else current_time
        reset_time = oldest_request + self.period
        
        return False, remaining_calls, reset_time
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and apply rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or rate limit error
        """
        # Skip rate limiting for bypass paths
        if self._should_bypass_check(request.url.path):
            return await call_next(request)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Check rate limit
        is_limited, remaining_calls, reset_time = self._is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(
                f"Rate limit exceeded for client {client_id} on {request.url.path}"
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.calls} per {self.period} seconds",
                    "retry_after": int(reset_time - time.time())
                },
                headers={
                    "X-RateLimit-Limit": str(self.calls),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(int(reset_time - time.time()))
                }
            )
        
        # Continue to next middleware
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.calls)
        response.headers["X-RateLimit-Remaining"] = str(remaining_calls)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        logger.debug(
            f"Request processed for client {client_id}: "
            f"{remaining_calls} calls remaining"
        )
        
        return response