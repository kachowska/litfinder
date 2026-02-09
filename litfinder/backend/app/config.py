"""
Application Configuration
Pydantic Settings for environment variables
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # App
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-this-secret-key"
    
    # Database
    database_url: str = "postgresql+asyncpg://litfinder:litfinder@localhost:5432/litfinder"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # API Keys
    claude_api_key: str = ""
    openalex_email: str = ""
    openai_api_key: str = ""
    
    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""
    
    # Rate limits
    rate_limit_free: int = 10
    rate_limit_pro: int = 1000
    
    # CORS
    cors_origins_str: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins_str.split(",")]
    
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
