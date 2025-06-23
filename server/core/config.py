"""Configuration management for Zoho MCP Server."""

import os
import secrets
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Zoho OAuth Configuration
    zoho_client_id: str = Field(default="", description="Zoho OAuth Client ID")
    zoho_client_secret: str = Field(default="", description="Zoho OAuth Client Secret")
    zoho_refresh_token: str = Field(default="", description="Zoho OAuth Refresh Token")
    portal_id: str = Field(default="", alias="ZOHO_PORTAL_ID", description="Zoho Portal ID")

    # JWT Configuration
    jwt_secret: str = Field(min_length=32, description="JWT Secret Key")
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")
    jwt_expire_hours: int = Field(default=12, ge=1, le=24, description="JWT Expiration Hours")

    @field_validator('jwt_secret')
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret and generate secure default if not provided."""
        if not v:
            # Generate a cryptographically secure secret
            generated_secret = secrets.token_urlsafe(32)
            print(f"WARNING: JWT_SECRET not provided. Generated secure secret: {generated_secret}")
            print("IMPORTANT: Save this secret to your .env file as JWT_SECRET=<secret>")
            print("CRITICAL: Do not use the same secret across environments!")
            return generated_secret

        # Ensure minimum security requirements
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters long")

        # Check for common weak secrets
        weak_secrets = [
            "default_jwt_secret_key_32_chars_long",
            "your-jwt-secret-key-here",
            "changeme",
            "secret",
            "password",
            "jwt_secret"
        ]

        if v.lower() in [w.lower() for w in weak_secrets]:
            raise ValueError(f"JWT secret '{v}' is too weak. Use a cryptographically secure random string.")

        return v

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_password: str = Field(default="", description="Redis Password")
    redis_ssl: bool = Field(default=False, description="Redis SSL Enabled")

    # Security Configuration
    allowed_ips: str = Field(
        default="127.0.0.1,::1",
        description="Allowed IP addresses/CIDR blocks (comma-separated)"
    )
    trusted_proxies: str = Field(
        default="",
        description="Trusted proxy IP addresses/CIDR blocks (comma-separated) that can set X-Forwarded-For headers"
    )
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Rate limit requests per minute"
    )

    # Application Configuration
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Log Level")
    debug: bool = Field(default=False, description="Debug Mode")

    # API Configuration
    api_base_url: str = Field(
        default="https://projectsapi.zoho.com/restapi",
        description="Zoho Projects API Base URL"
    )
    workdrive_api_url: str = Field(
        default="https://workdrive.zoho.com/api/v1",
        description="Zoho WorkDrive API URL"
    )

    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable Metrics")
    metrics_port: int = Field(default=9090, description="Metrics Port")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="CORS Origins (comma-separated)"
    )
    cors_credentials: bool = Field(default=True, description="CORS Credentials")

    # Cache Configuration
    cache_ttl_seconds: int = Field(default=300, description="Cache TTL Seconds")
    token_cache_ttl_seconds: int = Field(
        default=3300,
        description="Token Cache TTL Seconds"
    )

    # Webhook Configuration
    webhook_secret: str = Field(default="", description="Webhook Secret")
    enable_webhooks: bool = Field(default=True, description="Enable Webhooks")

    @field_validator('webhook_secret')
    @classmethod
    def validate_webhook_secret(cls, v):
        """Validate webhook secret configuration."""
        if v and len(v) < 16:
            raise ValueError("Webhook secret must be at least 16 characters long")

        # Check for weak webhook secrets
        if v:
            weak_secrets = [
                "webhook_secret",
                "changeme",
                "secret",
                "password",
                "your-webhook-secret",
                "your_webhook_secret_here"
            ]

            if v.lower() in [w.lower() for w in weak_secrets]:
                # In development, just warn instead of failing
                import os
                env = os.getenv('ENVIRONMENT', 'development').lower()
                if env == 'development':
                    print(f"WARNING: Webhook secret '{v}' is weak but allowed in development")
                    return ""  # Return empty string to disable webhook verification
                else:
                    raise ValueError(f"Webhook secret '{v}' is too weak. Use a cryptographically secure random string.")

        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
def get_settings() -> Settings:
    """Get settings instance."""
    return Settings()

settings = get_settings()
