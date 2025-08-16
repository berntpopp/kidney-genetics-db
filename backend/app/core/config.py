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

    # Background Tasks
    AUTO_UPDATE_ENABLED: bool = True

    # PubTator Configuration
    PUBTATOR_MAX_PAGES: int = 100  # Maximum pages to fetch per run
    PUBTATOR_USE_CACHE: bool = True  # Enable caching of PubTator results
    PUBTATOR_MIN_PUBLICATIONS: int = 3  # Minimum publications for gene inclusion
    PUBTATOR_SEARCH_QUERY: str = '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)'
    PUBTATOR_MIN_DATE: str = "2015"  # Focus on recent literature
    PUBTATOR_BATCH_SIZE: int = 100  # PMIDs per batch for annotation fetching
    PUBTATOR_RATE_LIMIT_DELAY: float = 0.3  # Seconds between API calls

    # PanelApp Configuration
    PANELAPP_CONFIDENCE_LEVELS: list[str] = ["green", "amber"]  # Confidence levels to include
    PANELAPP_MIN_EVIDENCE_LEVEL: int = 3  # Minimum evidence level
    PANELAPP_PANELS: list[int] = [384, 539]  # UK Panel IDs (kidney related)
    PANELAPP_AU_PANELS: list[int] = [217, 363]  # Australia Panel IDs (kidney related)

    # HPO Configuration
    HPO_KIDNEY_ROOT_TERMS: list[str] = ["HP:0000077", "HP:0000079"]  # Kidney/urinary abnormalities
    HPO_MIN_GENE_ASSOCIATIONS: int = 2  # Minimum associations for inclusion

    # ClinGen Configuration
    CLINGEN_DOWNLOAD_URL: str = "https://search.clinicalgenome.org/kb/gene-validity/download"
    CLINGEN_MIN_CLASSIFICATION: str = "Limited"  # Minimum classification level

    # GenCC Configuration
    GENCC_API_URL: str = "https://search.thegencc.org/api/submissions"
    GENCC_CONFIDENCE_CATEGORIES: list[str] = ["definitive", "strong", "moderate"]

    # Evidence Scoring Weights (matching PostgreSQL view)
    EVIDENCE_WEIGHTS: dict[str, float] = {
        "PanelApp": 0.25,
        "HPO": 0.15,
        "Literature": 0.20,
        "OMIM": 0.20,
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
