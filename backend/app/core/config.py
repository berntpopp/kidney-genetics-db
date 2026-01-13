"""
Configuration settings for the application
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Application
    APP_NAME: str = "Kidney Genetics API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics"
    DATABASE_ECHO: bool = False

    # Security - JWT
    JWT_SECRET_KEY: str = "13b45dbb75d5b321d69c6b71101c3d7b1e11d980cdb79b3eeab700d440b01c63"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security - Passwords
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12

    # Security - Account
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Default Admin (for initial setup only)
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@kidney-genetics.local"
    ADMIN_PASSWORD: str = "ChangeMe!Admin2024"  # Change immediately after first login

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
    ARQ_QUEUE_NAME: str = "kidney_genetics_tasks"
    ARQ_MAX_JOBS: int = 3  # Max concurrent jobs per worker
    ARQ_JOB_TIMEOUT: int = 7200  # 2 hours max per job
    USE_ARQ_WORKER: bool = False  # Feature flag: True = use ARQ, False = use in-process tasks

    # STRING-DB Configuration
    STRING_VERSION: str = "12.0"
    STRING_MIN_SCORE: int = 400
    STRING_MAX_INTERACTIONS_STORED: int = 30
    STRING_DATA_DIR: str = (
        "/home/bernt-popp/development/kidney-genetics-db/backend/data/string/v12.0"
    )
    STRING_CACHE_TTL_DAYS: int = 30

    # Gene Normalization
    HGNC_BATCH_SIZE: int = 50  # Genes per HGNC API batch request
    HGNC_RETRY_ATTEMPTS: int = 3  # Retry attempts for failed requests
    HGNC_CACHE_ENABLED: bool = True  # Enable HGNC response caching

    # Configuration System
    CONFIG_DIR: str = "./config"  # Directory for YAML configuration files
    ENVIRONMENT: str = "dev"  # Environment: dev, staging, prod

    # API Keys (optional)
    OPENAI_API_KEY: str | None = None

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
    POSTGRES_PASSWORD: str = "kidney_pass"
    POSTGRES_DB: str = "kidney_genetics"


# Create settings instance
settings = Settings()
