"""
Data source configuration settings

This module contains all configuration for data sources, including
display metadata, URLs, and documentation links.
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
    },
    "PubTator": {
        "display_name": "PubTator3",
        "description": "Automated literature mining for kidney disease genes from PubMed",
        "url": "https://www.ncbi.nlm.nih.gov/research/pubtator3/",
        "documentation_url": "https://www.ncbi.nlm.nih.gov/research/pubtator3/api",
        "auto_update": True,
        "priority": 2,
    },
    "ClinGen": {
        "display_name": "ClinGen",
        "description": "Expert-curated gene-disease validity assessments from 5 kidney specialist panels",
        "url": "https://clinicalgenome.org/",
        "documentation_url": "https://clinicalgenome.org/docs/gene-disease-validity/",
        "auto_update": True,
        "priority": 3,
    },
    "GenCC": {
        "display_name": "GenCC",
        "description": "Harmonized gene-disease relationships from 40+ submitters worldwide",
        "url": "https://thegencc.org/",
        "documentation_url": "https://thegencc.org/faq.html",
        "auto_update": True,
        "priority": 4,
    },
    "HPO": {
        "display_name": "HPO",
        "description": "Human Phenotype Ontology - Kidney/urinary phenotypes and associated genes",
        "url": "https://ontology.jax.org/",
        "documentation_url": "https://hpo.jax.org/app/data/annotations",
        "auto_update": True,  # Using HPO API for gene-disease associations
        "priority": 5,
    },
    "Literature": {
        "display_name": "Literature",
        "description": "Curated literature references",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Manual curation
        "priority": 6,
    },
    "Diagnostic": {
        "display_name": "Diagnostic Panels",
        "description": "Commercial diagnostic kidney gene panels",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Not yet implemented
        "priority": 7,
    },
}

# List of sources that support automatic updates
AUTO_UPDATE_SOURCES = [
    source for source, config in DATA_SOURCE_CONFIG.items()
    if config.get("auto_update", False)
]

# List of sources in priority order
PRIORITY_ORDERED_SOURCES = sorted(
    DATA_SOURCE_CONFIG.keys(),
    key=lambda x: DATA_SOURCE_CONFIG[x].get("priority", 999)
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
