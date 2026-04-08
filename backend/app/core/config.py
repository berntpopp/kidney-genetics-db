"""
Configuration settings for the application
"""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        secrets_dir="/run/secrets",
    )

    # Application
    APP_NAME: str = "Kidney Genetics API"
    APP_VERSION: str = "0.3.4"
    DEBUG: bool = False
    SITE_URL: str = "https://kidney-genetics.org"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Database — REQUIRED, no default (must be set via .env or env var)
    DATABASE_URL: SecretStr
    DATABASE_ECHO: bool = False

    # Security - JWT — REQUIRED, no default
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security - Passwords
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12

    # Security - Account
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Default Admin (for initial setup only) — REQUIRED, no default
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@kidney-genetics.local"
    ADMIN_PASSWORD: SecretStr
    ADMIN_FORCE_PASSWORD_RESET: bool = False  # Set True to update admin password on next restart

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    # Cache System Configuration
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 3600  # 1 hour default TTL
    CACHE_MAX_MEMORY_SIZE: int = 1000  # Maximum entries in memory cache
    CACHE_CLEANUP_INTERVAL: int = 3600  # Cleanup expired entries every hour
    CACHE_REDIS_URL: str | None = None  # Optional Redis URL for future use

    # HTTP Cache settings
    HTTP_CACHE_ENABLED: bool = True
    HTTP_CACHE_DIR: str = ".cache/http"
    HTTP_CACHE_MAX_SIZE_MB: int = 500  # Maximum cache size in MB
    HTTP_CACHE_TTL_DEFAULT: int = 3600  # Default HTTP cache TTL

    # Background Tasks
    AUTO_UPDATE_ENABLED: bool = True

    # Redis & ARQ Task Queue
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_RATE_LIMIT_DB: int = 1  # Separate DB from ARQ (DB 0)
    ARQ_QUEUE_NAME: str = "kidney_genetics_tasks"
    ARQ_MAX_JOBS: int = 3  # Max concurrent jobs per worker
    ARQ_JOB_TIMEOUT: int = 21600  # 6 hours max per job (annotation pipelines need this)
    USE_ARQ_WORKER: bool = False  # Feature flag: True = use ARQ, False = use in-process tasks

    # STRING-DB Configuration
    STRING_VERSION: str = "12.0"
    STRING_MIN_SCORE: int = 400
    STRING_MAX_INTERACTIONS_STORED: int = 30
    STRING_DATA_DIR: str = "./data/string/v12.0"
    STRING_CACHE_TTL_DAYS: int = 30

    # Gene Normalization
    HGNC_BATCH_SIZE: int = 50  # Genes per HGNC API batch request
    HGNC_RETRY_ATTEMPTS: int = 3  # Retry attempts for failed requests
    HGNC_CACHE_ENABLED: bool = True  # Enable HGNC response caching

    # Configuration System
    CONFIG_DIR: str = "./config"  # Directory for YAML configuration files
    ENVIRONMENT: str = "dev"  # Environment: dev, staging, prod

    # API Keys (optional)
    OPENAI_API_KEY: SecretStr | None = None

    # Zenodo DOI Integration
    ZENODO_API_TOKEN: SecretStr | None = None  # Personal access token from zenodo.org
    ZENODO_SANDBOX: bool = True  # True = sandbox.zenodo.org, False = zenodo.org
    ZENODO_COMMUNITY: str | None = None  # Optional community identifier

    # Backup Configuration
    BACKUP_DIR: str = "backups"  # Directory for backup files
    BACKUP_RETENTION_DAYS: int = 7  # How long to keep backups
    BACKUP_COMPRESSION_LEVEL: int = 6  # 0-9 for gzip compression
    BACKUP_PARALLEL_JOBS: int = 2  # Number of parallel dump/restore jobs
    BACKUP_MAX_SIZE_GB: int = 100  # Alert if backup exceeds this size

    # PostgreSQL connection for backups (extracted from DATABASE_URL by default)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "kidney_user"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str = "kidney_genetics"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: SecretStr) -> SecretStr:
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        placeholders = {"change_this_to_a_secure_secret_key", "changeme", "secret"}
        if secret.lower() in placeholders:
            raise ValueError("JWT_SECRET_KEY must not be a placeholder value")
        return v


# Create settings instance
settings = Settings()
