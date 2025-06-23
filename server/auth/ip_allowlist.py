"""IP allowlist middleware for Zoho MCP Server."""

import ipaddress
import logging
from typing import List, Optional, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class IPAllowlistMiddleware(BaseHTTPMiddleware):
    """Middleware to restrict access based on IP allowlist."""

    def __init__(
        self,
        app,
        allowed_ips: List[str],
        bypass_paths: Optional[List[str]] = None,
        trusted_proxies: Optional[List[str]] = None
    ) -> None:
        """Initialize IP allowlist middleware.

        Args:
            app: FastAPI application
            allowed_ips: List of allowed IP addresses or CIDR blocks
            bypass_paths: List of paths that bypass IP filtering
            trusted_proxies: List of trusted proxy IP addresses that can set X-Forwarded-For
        """
        super().__init__(app)
        self.allowed_networks = self._parse_ip_list(allowed_ips)
        self.trusted_proxy_networks = self._parse_ip_list(trusted_proxies or [])
        self.bypass_paths = bypass_paths or ["/health", "/docs", "/openapi.json"]

        logger.info(f"IP allowlist initialized with {len(self.allowed_networks)} networks")
        logger.info(f"Trusted proxies initialized with {len(self.trusted_proxy_networks)} networks")
        for network in self.allowed_networks:
            logger.debug(f"Allowed network: {network}")
        for network in self.trusted_proxy_networks:
            logger.debug(f"Trusted proxy network: {network}")

    def _parse_ip_list(
        self,
        ip_list: List[str]
    ) -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
        """Parse list of IP addresses and CIDR blocks.

        Args:
            ip_list: List of IP addresses or CIDR blocks

        Returns:
            List of IP network objects
        """
        networks = []

        for ip_str in ip_list:
            try:
                # Handle both single IPs and CIDR notation
                if '/' not in ip_str:
                    # Single IP address - add appropriate subnet mask
                    if ':' in ip_str:
                        # IPv6
                        ip_str = f"{ip_str}/128"
                    else:
                        # IPv4
                        ip_str = f"{ip_str}/32"

                network = ipaddress.ip_network(ip_str, strict=False)
                networks.append(network)

            except ValueError as e:
                logger.error(f"Invalid IP address or CIDR block '{ip_str}': {e}")
                continue

        return networks

    def _is_trusted_proxy(self, proxy_ip: str) -> bool:
        """Check if IP is a trusted proxy.

        Args:
            proxy_ip: Proxy IP address

        Returns:
            True if IP is a trusted proxy
        """
        try:
            proxy_addr = ipaddress.ip_address(proxy_ip)
            for network in self.trusted_proxy_networks:
                if proxy_addr in network:
                    return True
            return False
        except ValueError:
            return False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address
        """
        # Get the immediate client IP (could be proxy or real client)
        immediate_client = request.client.host if request.client else "unknown"

        # Only trust forwarded headers if they come from trusted proxies
        if self.trusted_proxy_networks and self._is_trusted_proxy(immediate_client):
            # Check for forwarded headers from trusted proxy
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # X-Forwarded-For can contain multiple IPs, get the first one (original client)
                client_ip = forwarded_for.split(",")[0].strip()
                logger.debug(f"Using X-Forwarded-For IP {client_ip} from trusted proxy {immediate_client}")
                return client_ip

            # Check for real IP header from trusted proxy
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                client_ip = real_ip.strip()
                logger.debug(f"Using X-Real-IP {client_ip} from trusted proxy {immediate_client}")
                return client_ip

        # If no trusted proxy headers or not from trusted proxy, use immediate client IP
        logger.debug(f"Using immediate client IP: {immediate_client}")
        return immediate_client

    def _is_ip_allowed(self, client_ip: str) -> bool:
        """Check if client IP is in allowlist.

        Args:
            client_ip: Client IP address

        Returns:
            True if IP is allowed
        """
        try:
            client_addr = ipaddress.ip_address(client_ip)

            for network in self.allowed_networks:
                if client_addr in network:
                    return True

            return False

        except ValueError as e:
            logger.warning(f"Invalid client IP address '{client_ip}': {e}")
            # For test environments, allow 'testclient' and 'unknown' IPs
            if client_ip in ['testclient', 'unknown'] and self._is_test_environment():
                return True
            return False

    def _is_test_environment(self) -> bool:
        """Check if running in test environment."""
        import os
        return os.getenv("ENVIRONMENT", "").lower() in ["test", "security_test"]

    def _should_bypass_check(self, path: str) -> bool:
        """Check if path should bypass IP filtering.

        Args:
            path: Request path

        Returns:
            True if should bypass check
        """
        return any(path.startswith(bypass_path) for bypass_path in self.bypass_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and check IP allowlist.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or error if IP not allowed
        """
        # Skip IP check for bypass paths
        if self._should_bypass_check(request.url.path):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is allowed
        if not self._is_ip_allowed(client_ip):
            logger.warning(
                f"Access denied for IP {client_ip} to {request.url.path}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Access denied: IP address not in allowlist"
                }
            )

        # Log successful access
        logger.debug(f"Access granted for IP {client_ip} to {request.url.path}")

        # Continue to next middleware
        return await call_next(request)
