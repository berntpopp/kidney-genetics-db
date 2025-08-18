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

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

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

    # Evidence Scoring Weights (matching PostgreSQL view)
    EVIDENCE_WEIGHTS: dict[str, float] = {
        "PanelApp": 0.25,
        "HPO": 0.15,
        "Literature": 0.20,
        "ClinGen": 0.10,
        "GenCC": 0.10,
    }

    # Gene Normalization
    HGNC_BATCH_SIZE: int = 50  # Genes per HGNC API batch request
    HGNC_RETRY_ATTEMPTS: int = 3  # Retry attempts for failed requests
    HGNC_CACHE_ENABLED: bool = True  # Enable HGNC response caching

    # Pipeline Configuration
    KIDNEY_FILTER_TERMS: list[str] = [
        "kidney",
        "renal",
        "nephro",
        "glomerul",
        "proteinuria",
        "hematuria",
        "nephrotic",
        "nephritic",
    ]

    # API Keys (optional)
    OPENAI_API_KEY: str | None = None


# Create settings instance
settings = Settings()
