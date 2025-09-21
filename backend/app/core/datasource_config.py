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
        # Kidney-related keywords for panel search
        "kidney_keywords": [
            "kidney",
            "renal",
            "nephro",
            "glomerul",
            # "tubul",  # REMOVED - too broad, matches tubulinopathies (brain disorders)
            "tubulopathy",  # More specific for kidney tubule disorders
            "tubulointerstitial",  # Specific for kidney tubule disorders
            "polycystic",
            "alport",
            "nephritis",
            "cystic kidney",  # More specific than just "cystic"
            "ciliopathy",  # Note: ciliopathies are multi-system, may need review
            "complement",
            "cakut",
            "focal segmental",
            "steroid resistant",
            "nephrotic",
            "proteinuria",
            "hematuria",
        ],
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
        # Rate limiting - CRITICAL for API compliance
        "requests_per_second": 3.0,  # PubTator3 official limit - DO NOT exceed
        # Search configuration
        "max_pages": None,  # None = unlimited, process all pages
        # Update modes configuration
        "smart_update": {
            "max_pages": 500,  # Stop after 500 pages max for smart updates
            "duplicate_threshold": 0.9,  # Stop at 90% duplicates
            "consecutive_pages": 3,  # Need 3 consecutive high-duplicate pages
        },
        "full_update": {
            "max_pages": None,  # No limit (get all pages) for full updates
        },
        "min_publications": 1,  # Minimum publications for gene inclusion (1 = include everything)
        "min_publications_enabled": True,  # Enable filtering for PubTator (threshold of 1 includes all)
        "filter_after_complete": True,  # Apply filter after all chunks processed
        "search_query": '("kidney disease" OR "renal disease") AND (gene OR syndrome) AND (variant OR mutation)',
        "batch_size": 100,  # PMIDs per batch for annotation fetching
        # Optimized chunking for more frequent saves and reduced memory
        "chunk_size": 300,  # Reduced from 1000 - more frequent saves
        "transaction_size": 1000,  # Reduced from 5000 - more frequent commits
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
        # Kidney-related keywords for disease filtering
        "kidney_keywords": [
            "kidney",
            "renal",
            "nephro",
            "glomerul",
            # "tubul",  # REMOVED - too broad, matches tubulinopathies (brain disorders)
            "tubulopathy",  # More specific for kidney tubule disorders
            "tubulointerstitial",  # Specific for kidney tubule disorders
            "polycystic",
            "alport",
            "nephritis",
            "cystic kidney",  # More specific than just "cystic"
            "ciliopathy",  # Note: ciliopathies are multi-system, may need review
            "complement",
            "cakut",
        ],
        # Classification weights for evidence scoring
        "classification_weights": {
            "Definitive": 1.0,
            "Strong": 0.8,
            "Moderate": 0.6,
            "Supportive": 0.5,
            "Limited": 0.3,
            "Disputed Evidence": 0.1,
            "No Known Disease Relationship": 0.0,
            "Refuted Evidence": 0.0,
        },
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
        # Syndromic classification configuration (matching R implementation)
        "syndromic_indicators": {
            "growth": "HP:0001507",  # Growth abnormality
            "skeletal": "HP:0000924",  # Skeletal system abnormality
            "neurologic": "HP:0000707",  # Abnormality of the nervous system
            "head_neck": "HP:0000152",  # Head and neck abnormality
        },
        # Classification configuration
        "clinical_groups": {
            "complement": {
                "signature_terms": [
                    "HP:0000093",  # Proteinuria
                    "HP:0000100",  # Nephrotic syndrome
                    "HP:0001970",  # Tubulointerstitial nephritis
                    "HP:0000796",  # Urethral obstruction
                    "HP:0003259",  # Elevated serum creatinine
                ],
                "name": "Complement-mediated kidney diseases",
                "weight": 1.0,
            },
            "cakut": {
                "signature_terms": [
                    "HP:0000107",  # Renal cyst
                    "HP:0000085",  # Horseshoe kidney
                    "HP:0000089",  # Renal hypoplasia
                    "HP:0000072",  # Hydroureter
                    "HP:0000126",  # Hydronephrosis
                ],
                "name": "Congenital anomalies of kidney and urinary tract",
                "weight": 1.0,
            },
            "glomerulopathy": {
                "signature_terms": [
                    "HP:0000097",  # Glomerulonephritis
                    "HP:0003774",  # Stage 5 chronic kidney disease
                    "HP:0000123",  # Nephritis
                    "HP:0000099",  # Glomerulosclerosis
                    "HP:0030888",  # C3 glomerulopathy
                ],
                "name": "Glomerular diseases",
                "weight": 1.0,
            },
            "cyst_cilio": {
                "signature_terms": [
                    "HP:0005562",  # Multiple renal cysts
                    "HP:0000107",  # Renal cyst
                    "HP:0001737",  # Pancreatic cysts
                    "HP:0000092",  # Renal tubular atrophy
                    "HP:0000003",  # Multicystic kidney dysplasia
                ],
                "name": "Cystic and ciliopathy disorders",
                "weight": 1.0,
            },
            "tubulopathy": {
                "signature_terms": [
                    "HP:0003127",  # Hypocalciuria
                    "HP:0002900",  # Hypokalemia
                    "HP:0002148",  # Hypophosphatemia
                    "HP:0000114",  # Proximal tubulopathy
                    "HP:0004918",  # Hyperchloremic metabolic acidosis
                ],
                "name": "Tubular disorders",
                "weight": 1.0,
            },
            "nephrolithiasis": {
                "signature_terms": [
                    "HP:0000787",  # Nephrolithiasis
                    "HP:0000121",  # Nephrocalcinosis
                    "HP:0000791",  # Uric acid nephrolithiasis
                    "HP:0008672",  # Calcium oxalate nephrolithiasis
                    "HP:0004724",  # Calcium nephrolithiasis
                ],
                "name": "Kidney stones and nephrocalcinosis",
                "weight": 1.0,
            },
        },
        "onset_groups": {
            "adult": {
                "root_term": "HP:0003581",
                "name": "Adult onset",
            },
            "pediatric": {
                "root_terms": ["HP:0410280", "HP:0003623"],
                "name": "Pediatric/Neonatal onset",
            },
            "congenital": {
                "root_terms": ["HP:0003577", "HP:0030674"],
                "name": "Congenital/Antenatal onset",
            },
        },
    },
    "DiagnosticPanels": {
        "display_name": "Diagnostic Panels",
        "description": "Commercial diagnostic kidney gene panels from multiple providers",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Manual upload via API
        "priority": 6,
        "hybrid_source": True,  # Uses unified source pattern
        "min_panels": 1,  # Minimum number of providers (panels) for gene inclusion (1 = include everything)
        "min_panels_enabled": True,  # Enabled but threshold of 1 includes all genes
    },
    "Literature": {
        "display_name": "Literature",
        "description": "Kidney disease genes from curated literature publications",
        "url": None,
        "documentation_url": None,
        "auto_update": False,  # Manual upload via API
        "priority": 7,
        "hybrid_source": True,  # Uses unified source pattern
        "min_publications": 1,  # Minimum publications for gene inclusion (1 = include everything)
        "min_publications_enabled": True,  # Enabled but threshold of 1 includes all genes
    },
}

# Internal process configurations with display metadata
INTERNAL_PROCESS_CONFIG: dict[str, dict[str, Any]] = {
    "annotation_pipeline": {
        "display_name": "Gene Annotation Pipeline",
        "description": "Post-processing pipeline that adds ClinVar annotations and computed scores",
        "category": "internal_process",
        "icon": "mdi-cog",
    },
    "Evidence_Aggregation": {
        "display_name": "Evidence Aggregation",
        "description": "Combines and scores evidence from all data sources",
        "category": "internal_process",
        "icon": "mdi-chart-timeline-variant",
    },
    "HGNC_Normalization": {
        "display_name": "HGNC Normalization",
        "description": "Normalizes gene symbols using HGNC database",
        "category": "internal_process",
        "icon": "mdi-format-align-center",
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


def get_internal_process_config(process_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific internal process"""
    return INTERNAL_PROCESS_CONFIG.get(process_name)


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


# Annotation source configurations with retry and rate limiting settings
ANNOTATION_SOURCE_CONFIG: dict[str, dict[str, Any]] = {
    "gnomad": {
        "requests_per_second": 3.0,
        "max_retries": 5,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
    },
    "clinvar": {
        "requests_per_second": 2.5,  # NCBI limit without API key
        "max_retries": 5,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
        # Review status confidence levels
        "review_confidence": {
            "practice guideline": 4,
            "reviewed by expert panel": 4,
            "criteria provided, multiple submitters, no conflicts": 3,
            "criteria provided, conflicting classifications": 2,
            "criteria provided, single submitter": 2,
            "no assertion for the individual variant": 1,
            "no assertion criteria provided": 1,
            "no classification provided": 0,
        },
    },
    "hpo": {
        "requests_per_second": 10.0,
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
    },
    "mpo_mgi": {
        "requests_per_second": 2.0,  # MGI servers are slower
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "hgnc": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "string_ppi": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "gtex": {
        "requests_per_second": 3.0,
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "descartes": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 90,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
}


def get_annotation_config(source_name: str) -> dict[str, Any] | None:
    """Get configuration for a specific annotation source"""
    return ANNOTATION_SOURCE_CONFIG.get(source_name)
