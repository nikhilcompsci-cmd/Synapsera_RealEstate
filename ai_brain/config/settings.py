from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "AI Brain - Real Estate Document Analysis"
    app_version: str = "0.1.0"
    debug: bool = True
    environment: str = "development"  # development, staging, production
    
    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_file: str = "logs/app.log"
    log_to_console: bool = True
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/ai_brain"
    db_echo: bool = False
    
    # API
    api_v1_prefix: str = "/api/v1"
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Celery (Task Queue)
    celery_broker_url: str = "redis://localhost:6379/0"  # Redis as message broker
    celery_result_backend: str = "redis://localhost:6379/1"  # Redis for results
    
    # Data Storage
    data_dir: str = "data"  # Base directory for uploads, indexes, etc.
    
    # Sentry (Error Tracking & Monitoring)
    sentry_dsn: str = ""  # Sentry Data Source Name
    sentry_environment: str = "development"  # Sentry environment tag
    sentry_traces_sample_rate: float = 1.0  # 100% transaction sampling
    sentry_enabled: bool = False  # Enable/disable Sentry
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'  # Allow extra fields in .env (e.g., OpenAI config)
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
