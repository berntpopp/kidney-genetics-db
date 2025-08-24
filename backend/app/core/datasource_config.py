"""
Data source configuration settings

This module contains all configuration for data sources, including
display metadata, URLs, documentation links, and source-specific parameters.
REFACTORED: Centralized all data source configurations from config.py
"""

from typing import Any

# Data source configurations with display metadata
DATA_SOURCE_CONFIG: dict[str, dict[str, Any]] = {
    "PanelApp": {
        "display_name": "PanelApp",
        "description": "Expert-curated gene panels from UK Genomics England and Australian Genomics",
        "url": "https://panelapp.genomicsengland.co.uk/",
        "documentation_url": "https://panelapp.genomicsengland.co.uk/api/docs/",
        "auto_update": True,
        "priority": 1,
        # API URLs
        "uk_api_url": "https://panelapp.genomicsengland.co.uk/api/v1",
        "au_api_url": "https://panelapp-aus.org/api/v1",
        # Panel configuration
        "uk_panels": [384, 539],  # UK Panel IDs (kidney related)
        "au_panels": [217, 363],  # Australia Panel IDs (kidney related)
        "confidence_levels": ["green", "amber"],  # Confidence levels to include
        "min_evidence_level": 3,  # Minimum evidence level
        # Cache settings
        "cache_ttl": 21600,  # 6 hours - moderate update frequency
    },
    "PubTator": {
        "display_name": "PubTator3",
        "description": "Automated literature mining for kidney disease genes from PubMed",
        "url": "https://www.ncbi.nlm.nih.gov/research/pubtator3/",
        "documentation_url": "https://www.ncbi.nlm.nih.gov/research/pubtator3/api",
        "auto_update": True,
        "priority": 2,
        # API settings
        "api_url": "https://www.ncbi.nlm.nih.gov/research/pubtator-api",
        # Search configuration
        "max_pages": 100,  # Maximum pages to fetch per run
        "min_publications": 3,  # Minimum publications for gene inclusion
        "search_query": '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)',
        "min_date": "2015",  # Focus on recent literature
        "batch_size": 100,  # PMIDs per batch for annotation fetching
        "rate_limit_delay": 0.3,  # Seconds between API calls
        # Cache settings
        "cache_ttl": 604800,  # 7 days - literature updates periodically
        "use_cache": True,  # Enable caching of PubTator results
    },
    "ClinGen": {
        "display_name": "ClinGen",
        "description": "Expert-curated gene-disease validity assessments from 5 kidney specialist panels",
        "url": "https://clinicalgenome.org/",
        "documentation_url": "https://clinicalgenome.org/docs/gene-disease-validity/",
        "auto_update": True,
        "priority": 3,
        # API settings
        "api_url": "https://search.clinicalgenome.org/api",
        "download_url": "https://search.clinicalgenome.org/kb/gene-validity/download",
        # Classification settings
        "min_classification": "Limited",  # Minimum classification level
        # Kidney-specific affiliate/expert panel IDs
        "kidney_affiliate_ids": [
            40066,  # Kidney Cystic and Ciliopathy Disorders
            40068,  # Glomerulopathy
            40067,  # Tubulopathy
            40069,  # Complement-Mediated Kidney Diseases
            40070,  # Congenital Anomalies of the Kidney and Urinary Tract
        ],
        # Cache settings
        "cache_ttl": 86400,  # 24 hours - stable classification data
    },
    "GenCC": {
        "display_name": "GenCC",
        "description": "Harmonized gene-disease relationships from 40+ submitters worldwide",
        "url": "https://thegencc.org/",
        "documentation_url": "https://thegencc.org/faq.html",
        "auto_update": True,
        "priority": 4,
        # API settings
        "api_url": "https://search.thegencc.org/api/submissions",
        "excel_url": "https://search.thegencc.org/download/action/submissions-export-csv",
        # Filtering settings
        "confidence_categories": ["definitive", "strong", "moderate"],
        # Cache settings
        "cache_ttl": 43200,  # 12 hours - regular submission updates
    },
    "HPO": {
        "display_name": "HPO",
        "description": "Human Phenotype Ontology - Kidney/urinary phenotypes and associated genes",
        "url": "https://ontology.jax.org/",
        "documentation_url": "https://hpo.jax.org/app/data/annotations",
        "auto_update": True,  # Using HPO API for gene-disease associations
        "priority": 5,
        # API settings
        "api_url": "https://ontology.jax.org/api",
        "browser_url": "https://hpo.jax.org",
        # Kidney phenotype configuration
        "kidney_root_term": "HP:0010935",  # Abnormality of the upper urinary tract
        "kidney_root_terms": ["HP:0000077", "HP:0000079"],  # Legacy - kept for compatibility
        "kidney_terms": [
            "HP:0010935",  # Abnormality of upper urinary tract
            "HP:0000077",  # Abnormality of the kidney
            "HP:0012210",  # Abnormal renal morphology
            "HP:0000079",  # Abnormality of the urinary system
        ],
        # Processing settings
        "min_gene_associations": 1,  # Minimum associations for inclusion
        "max_depth": 10,  # Maximum depth for descendant traversal
        "batch_size": 5,  # Number of concurrent requests (with exponential backoff)
        "request_delay": 0.2,  # Small delay between batches (backoff handles rate limiting)
        # Cache settings
        "cache_ttl": 604800,  # 7 days - stable ontology releases
    },
    "DiagnosticPanels": {
        "display_name": "Diagnostic Panels",
        "description": "Commercial diagnostic kidney gene panels from multiple providers",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Manual upload via API
        "priority": 6,
        "hybrid_source": True,  # Uses unified source pattern
    },
    "Literature": {
        "display_name": "Literature",
        "description": "Kidney disease genes from curated literature publications",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Manual upload via API
        "priority": 7,
        "hybrid_source": True,  # Uses unified source pattern
    },
}

# List of sources that support automatic updates
AUTO_UPDATE_SOURCES = [
    source for source, config in DATA_SOURCE_CONFIG.items() if config.get("auto_update", False)
]

# List of sources in priority order
PRIORITY_ORDERED_SOURCES = sorted(
    DATA_SOURCE_CONFIG.keys(), key=lambda x: DATA_SOURCE_CONFIG[x].get("priority", 999)
)


def get_source_config(source_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific data source"""
    return DATA_SOURCE_CONFIG.get(source_name)


def get_all_source_names() -> list[str]:
    """Get list of all configured data source names"""
    return list(DATA_SOURCE_CONFIG.keys())


def get_auto_update_sources() -> list[str]:
    """Get list of sources that support automatic updates"""
    return AUTO_UPDATE_SOURCES.copy()


def is_source_configured(source_name: str) -> bool:
    """Check if a data source is configured"""
    return source_name in DATA_SOURCE_CONFIG


def get_source_parameter(source_name: str, param_name: str, default: Any = None) -> Any:
    """
    Get a specific parameter for a data source.

    Args:
        source_name: Name of the data source
        param_name: Name of the parameter
        default: Default value if parameter not found

    Returns:
        Parameter value or default
    """
    config = get_source_config(source_name)
    if config:
        return config.get(param_name, default)
    return default


def get_source_cache_ttl(source_name: str) -> int:
    """
    Get cache TTL for a data source.

    Args:
        source_name: Name of the data source

    Returns:
        Cache TTL in seconds, defaults to 3600 (1 hour)
    """
    return get_source_parameter(source_name, "cache_ttl", 3600)


def get_source_api_url(source_name: str) -> str | None:
    """
    Get API URL for a data source.

    Args:
        source_name: Name of the data source

    Returns:
        API URL or None
    """
    return get_source_parameter(source_name, "api_url")
