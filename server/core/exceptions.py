"""Custom exception hierarchy for Zoho MCP Server."""

from typing import Any, Optional


class MCPError(Exception):
    """Base exception for all MCP server errors."""

    def __init__(self, message: str, code: int = -32603, data: Any = None):
        """Initialize MCP error.

        Args:
            message: Error message
            code: JSON-RPC error code
            data: Additional error data
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-RPC error format.

        Returns:
            Error dictionary for JSON-RPC response
        """
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            error["data"] = self.data
        return error


class ValidationError(MCPError):
    """Invalid input data or parameters."""

    def __init__(self, message: str, field: Optional[str] = None):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field name that failed validation
        """
        super().__init__(message, code=-32602)  # Invalid params
        self.field = field


class AuthenticationError(MCPError):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed"):
        """Initialize authentication error.

        Args:
            message: Error message
        """
        super().__init__(message, code=-32001)  # Custom auth error


class AuthorizationError(MCPError):
    """Authorization/permission denied."""

    def __init__(self, message: str = "Access denied"):
        """Initialize authorization error.

        Args:
            message: Error message
        """
        super().__init__(message, code=-32002)  # Custom auth error


class RateLimitError(MCPError):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
        """
        data = {"retry_after": retry_after} if retry_after is not None else None
        super().__init__(message, code=-32003, data=data)
        self.retry_after = retry_after


class ExternalAPIError(MCPError):
    """External API call failed."""

    def __init__(self, message: str, service: str, status_code: Optional[int] = None):
        """Initialize external API error.

        Args:
            message: Error message
            service: Service name (e.g., "zoho_projects", "zoho_workdrive")
            status_code: HTTP status code if available
        """
        data = {
            "service": service,
            "status_code": status_code
        }
        super().__init__(message, code=-32004, data=data)
        self.service = service
        self.status_code = status_code


class ConfigurationError(MCPError):
    """Configuration or setup error."""

    def __init__(self, message: str, config_field: Optional[str] = None):
        """Initialize configuration error.

        Args:
            message: Error message
            config_field: Configuration field that's problematic
        """
        data = {"config_field": config_field} if config_field else None
        super().__init__(message, code=-32005, data=data)
        self.config_field = config_field


class ResourceNotFoundError(MCPError):
    """Requested resource not found."""

    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        """Initialize resource not found error.

        Args:
            message: Error message
            resource_type: Type of resource (e.g., "project", "task", "file")
            resource_id: ID of the resource
        """
        data = {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        super().__init__(message, code=-32006, data=data)
        self.resource_type = resource_type
        self.resource_id = resource_id


class TemporaryError(MCPError):
    """Temporary error that might succeed if retried."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        """Initialize temporary error.

        Args:
            message: Error message
            retry_after: Suggested retry delay in seconds
        """
        data = {"retry_after": retry_after, "retryable": True} if retry_after else {"retryable": True}
        super().__init__(message, code=-32007, data=data)
        self.retry_after = retry_after


class SecurityError(MCPError):
    """Security-related error."""

    def __init__(self, message: str, security_type: Optional[str] = None):
        """Initialize security error.

        Args:
            message: Error message
            security_type: Type of security issue (e.g., "invalid_token", "ip_blocked")
        """
        data = {"security_type": security_type} if security_type else None
        super().__init__(message, code=-32008, data=data)
        self.security_type = security_type


class TimeoutError(MCPError):
    """Operation timed out."""

    def __init__(self, message: str = "Operation timed out", timeout_duration: Optional[float] = None):
        """Initialize timeout error.

        Args:
            message: Error message
            timeout_duration: Timeout duration in seconds
        """
        data = {"timeout_duration": timeout_duration} if timeout_duration else None
        super().__init__(message, code=-32009, data=data)
        self.timeout_duration = timeout_duration


# Legacy compatibility - for existing ZohoAPIError
class ZohoAPIError(ExternalAPIError):
    """Zoho API specific error (legacy compatibility)."""

    def __init__(self, message: str, status_code: int, response_data: Any = None):
        """Initialize Zoho API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response_data: Response data from Zoho API
        """
        super().__init__(message, service="zoho_api", status_code=status_code)
        self.response_data = response_data
        if response_data is not None:
            self.data["response_data"] = response_data