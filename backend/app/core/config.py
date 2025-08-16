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

    # External APIs
    PANELAPP_UK_URL: str = "https://panelapp.genomicsengland.co.uk/api/v1"
    PANELAPP_AU_URL: str = "https://panelapp-aus.org/api/v1"
    HPO_API_URL: str = "https://ontology.jax.org/api"
    PUBTATOR_API_URL: str = "https://www.ncbi.nlm.nih.gov/research/pubtator-api"
    HGNC_API_URL: str = "http://rest.genenames.org"

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
