"""Configuration management for Zoho MCP Server."""

from typing import List
from pydantic import Field
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
    zoho_client_id: str = Field(..., description="Zoho OAuth Client ID")
    zoho_client_secret: str = Field(..., description="Zoho OAuth Client Secret")
    zoho_refresh_token: str = Field(..., description="Zoho OAuth Refresh Token")
    portal_id: str = Field(..., description="Zoho Portal ID")
    
    # JWT Configuration
    jwt_secret: str = Field(..., min_length=32, description="JWT Secret Key")
    jwt_algorithm: str = Field(default="HS256", description="JWT Algorithm")
    jwt_expire_hours: int = Field(default=12, ge=1, le=24, description="JWT Expiration Hours")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    redis_password: str = Field(default="", description="Redis Password")
    redis_ssl: bool = Field(default=False, description="Redis SSL Enabled")
    
    # Security Configuration
    allowed_ips: List[str] = Field(
        default=["127.0.0.1", "::1"],
        description="Allowed IP addresses/CIDR blocks"
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
        default="https://www.zohoapis.com/workdrive/api/v1",
        description="Zoho WorkDrive API URL"
    )
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable Metrics")
    metrics_port: int = Field(default=9090, description="Metrics Port")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        description="CORS Origins"
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
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()