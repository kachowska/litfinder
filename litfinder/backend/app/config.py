"""
Application Configuration
Pydantic Settings for environment variables
"""
from typing import List
from pydantic import ConfigDict, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App
    app_env: str = "development"
    debug: bool = True
    secret_key: str  # Must be provided via environment
    
    # Database
    database_url: str = "postgresql+asyncpg://litfinder:litfinder@localhost:5432/litfinder"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # API Keys
    claude_api_key: str = ""
    gemini_api_key: str = ""
    openalex_email: str = ""
    openalex_api_key: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    
    # Rate limits
    rate_limit_free: int = 10
    rate_limit_pro: int = 1000

    # Security
    fail_closed_on_cache_error: bool = True  # Fail-closed (secure) by default

    # JWT settings
    jwt_secret_key: str = ""  # If empty, falls back to secret_key (see security.py)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_minutes: int = 10080  # 7 days (60 * 24 * 7)

    # CORS
    cors_origins_str: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    @model_validator(mode='after')
    def validate_production_secrets(self) -> 'Settings':
        """
        Validate that production environment has secure secrets configured.

        Fails fast on startup if production is using placeholder/insecure secrets.
        This prevents accidentally deploying with default development secrets.
        """
        if not self.is_production:
            # Development/test environments can use any secrets
            return self

        # Minimum secret length for security (32 characters = 256 bits in hex)
        MIN_SECRET_LENGTH = 32

        # Known insecure placeholder values
        insecure_values = {
            "change-this-secret-key",
            "change-this-secret-key-in-production",
            "dev-secret",
            "test-secret",
            "secret",
            "password"
        }

        # Check secret_key
        if not self.secret_key or len(self.secret_key) < MIN_SECRET_LENGTH:
            raise ValueError(
                "Production environment detected with empty or short secret_key. "
                "Please set SECRET_KEY environment variable to a strong random value (minimum 32 characters). "
                "Generate one with: openssl rand -hex 32"
            )

        if self.secret_key.lower() in insecure_values:
            raise ValueError(
                "Production environment detected with insecure secret_key. "
                "Please set SECRET_KEY environment variable to a strong random value. "
                "Generate one with: openssl rand -hex 32"
            )

        # Check jwt_secret_key (if provided; empty string means fallback to secret_key)
        if self.jwt_secret_key:
            if len(self.jwt_secret_key) < MIN_SECRET_LENGTH:
                raise ValueError(
                    "Production environment detected with short jwt_secret_key. "
                    "Please set JWT_SECRET_KEY environment variable to a strong random value (minimum 32 characters). "
                    "Generate one with: openssl rand -hex 32"
                )

            if self.jwt_secret_key.lower() in insecure_values:
                raise ValueError(
                    "Production environment detected with insecure jwt_secret_key. "
                    "Please set JWT_SECRET_KEY environment variable to a strong random value. "
                    "Generate one with: openssl rand -hex 32"
                )

        return self

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_str.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
