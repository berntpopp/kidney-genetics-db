"""
Gene filter configuration for removing false positives.

This module contains lists of terms that are commonly mistaken for genes
but are actually disease names, test codes, technical terms, etc.
These should be filtered out during gene extraction.
"""

# Disease and syndrome abbreviations
DISEASE_ABBREVIATIONS = {
    "ADHD",     # Attention Deficit Hyperactivity Disorder
    "AIDS",     # Acquired Immunodeficiency Syndrome
    "ADTKD",    # Autosomal Dominant Tubulointerstitial Kidney Disease
    "BOFS",     # Branchio-Oto-Facial Syndrome
    "BOS",      # Bohring-Opitz Syndrome
    "CAKUT",    # Congenital Anomalies of Kidney and Urinary Tract
    "DSD",      # Disorders of Sex Development
    "FSGS",     # Focal Segmental Glomerulosclerosis
    "ESKD",     # End-Stage Kidney Disease
    "CKD",      # Chronic Kidney Disease
    "AKI",      # Acute Kidney Injury
    "IGA",      # IgA Nephropathy (when not referring to IGA gene)
    "ARPKD",    # Autosomal Recessive Polycystic Kidney Disease
    "ADPKD",    # Autosomal Dominant Polycystic Kidney Disease
}

# HLA typing markers (not actual genes)
HLA_MARKERS = {
    "HLA",      # Generic HLA reference
    "HLA01",    # HLA typing code
    "DPA1",     # HLA-DPA1 typing
    "DPB1",     # HLA-DPB1 typing
    "DQA1",     # HLA-DQA1 typing
    "DQB1",     # HLA-DQB1 typing
    "DRB1",     # HLA-DRB1 typing
    "DRB3",     # HLA-DRB3 typing
    "DRB4",     # HLA-DRB4 typing
    "DRB5",     # HLA-DRB5 typing
}

# Technical and methodology terms
TECHNICAL_TERMS = {
    # Company/database names
    "CENTOGENE",
    "HGMD",     # Human Gene Mutation Database
    "OMIM",     # Online Mendelian Inheritance in Man
    
    # Lab/testing terms
    "CLIA",     # Clinical Laboratory Improvement Amendments
    "CNV",      # Copy Number Variation
    "DIN",      # German Industrial Standard
    "EDTA",     # Ethylenediaminetetraacetic acid
    "ES",       # Exome Sequencing
    "WES",      # Whole Exome Sequencing
    "WGS",      # Whole Genome Sequencing
    "ISO",      # International Organization for Standardization
    "NGS",      # Next Generation Sequencing
    "NIPT",     # Non-Invasive Prenatal Testing
    "PGX",      # Pharmacogenomics
    "TSO500",   # Illumina TruSight Oncology 500
    "VNTR",     # Variable Number Tandem Repeat
    "MLPA",     # Multiplex Ligation-dependent Probe Amplification
    "PCR",      # Polymerase Chain Reaction
    "FISH",     # Fluorescence In Situ Hybridization
    "CGH",      # Comparative Genomic Hybridization
    "SNP",      # Single Nucleotide Polymorphism
    "INDEL",    # Insertion/Deletion
    "LOH",      # Loss of Heterozygosity
}

# Panel codes and identifiers
PANEL_CODES = {
    # CeGaT kidney panel codes
    "KID01", "KID02", "KID03", "KID04", "KID05",
    "KID06", "KID07", "KID08", "KID09", "KID10",
    "KID11", "KID12", "KID13", "KID14", "KID15",
    "KID16", "KID17", "KID18", "KID19", "KID20",
    "KID21",
    
    # Other panel codes
    "BRN07",    # Brain panel
    "CIL03",    # Ciliopathy panel
    "NEU01",    # Neurology panel
    "MET01",    # Metabolism panel
    "IMM01",    # Immunology panel
}

# Ambiguous or partial identifiers
AMBIGUOUS_TERMS = {
    "ID",       # Too generic
    "ES",       # Exome Sequencing
    "RPS",      # Could be ribosomal protein but too ambiguous
    "PASNA",    # Unknown abbreviation
    "NKX2",     # Incomplete gene family reference (should be NKX2-1, NKX2-2, etc.)
    "NKX3",     # Incomplete gene family reference (should be NKX3-1, NKX3-2)
}

# Special cases that need context-aware filtering
SPECIAL_CASES = {
    "ZNF423MLPA": "ZNF423",  # Extract the gene part, remove the method suffix
}

# Combine all filter sets
FILTER_TERMS = (
    DISEASE_ABBREVIATIONS |
    HLA_MARKERS |
    TECHNICAL_TERMS |
    PANEL_CODES |
    AMBIGUOUS_TERMS
)

def should_filter_gene(gene_symbol: str) -> bool:
    """
    Check if a gene symbol should be filtered out as a false positive.
    
    Args:
        gene_symbol: The gene symbol to check
        
    Returns:
        True if the symbol should be filtered out, False otherwise
    """
    # Direct match
    if gene_symbol.upper() in FILTER_TERMS:
        return True
    
    # Check for panel code patterns
    if gene_symbol.upper().startswith(("KID", "BRN", "CIL", "NEU", "MET", "IMM")):
        # Check if it matches pattern like KID01, BRN07, etc.
        if len(gene_symbol) >= 5 and gene_symbol[-2:].isdigit():
            return True
    
    # Check for HLA patterns
    if gene_symbol.upper().startswith("HLA-"):
        return True
    
    return False

def clean_gene_symbol(gene_symbol: str) -> str:
    """
    Clean a gene symbol by removing method suffixes or other additions.
    
    Args:
        gene_symbol: The gene symbol to clean
        
    Returns:
        Cleaned gene symbol or empty string if it should be filtered
    """
    # Check special cases
    if gene_symbol in SPECIAL_CASES:
        return SPECIAL_CASES[gene_symbol]
    
    # Remove common method suffixes
    for suffix in ["MLPA", "FISH", "PCR", "SEQ", "CNV"]:
        if gene_symbol.endswith(suffix) and len(gene_symbol) > len(suffix):
            # Check if what remains is a valid gene pattern
            potential_gene = gene_symbol[:-len(suffix)]
            if potential_gene and not should_filter_gene(potential_gene):
                return potential_gene
    
    # Return original if no cleaning needed
    return gene_symbol if not should_filter_gene(gene_symbol) else ""

def get_filter_reason(gene_symbol: str) -> str:
    """
    Get the reason why a gene symbol is being filtered.
    
    Args:
        gene_symbol: The gene symbol to check
        
    Returns:
        String describing why the symbol is filtered, or empty if not filtered
    """
    upper_symbol = gene_symbol.upper()
    
    if upper_symbol in DISEASE_ABBREVIATIONS:
        return "Disease/syndrome abbreviation"
    elif upper_symbol in HLA_MARKERS:
        return "HLA typing marker"
    elif upper_symbol in TECHNICAL_TERMS:
        return "Technical/methodology term"
    elif upper_symbol in PANEL_CODES:
        return "Panel code identifier"
    elif upper_symbol in AMBIGUOUS_TERMS:
        return "Ambiguous/incomplete identifier"
    elif upper_symbol.startswith("HLA-"):
        return "HLA typing variant"
    elif upper_symbol.startswith(("KID", "BRN", "CIL")) and len(upper_symbol) >= 5 and upper_symbol[-2:].isdigit():
        return "Panel code pattern"
    
    return ""