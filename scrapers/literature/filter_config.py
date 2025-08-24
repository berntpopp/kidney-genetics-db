"""
Literature-specific gene filter configuration for removing false positives.

This module contains lists of terms that are commonly mistaken for genes
in literature extraction but are actually disease names, generic terms,
descriptive words, etc. These should be filtered out during gene extraction.
"""

# Disease and syndrome names that appear in literature
DISEASE_SYNDROME_NAMES = {
    "Alport",         # Alport syndrome
    "Bardet",         # Bardet-Biedl syndrome  
    "Bartter",        # Bartter syndrome
    "Denys-Drash",    # Denys-Drash syndrome
    "Fanconi",        # Fanconi syndrome
    "Frasier",        # Frasier syndrome
    "Hajdu-Cheney",   # Hajdu-Cheney syndrome
    "Joubert",        # Joubert syndrome
    "Lowe",           # Lowe syndrome
    "Meckel",         # Meckel syndrome
    "Senior-Loken",   # Senior-Loken syndrome
    "Townes-Brocks",  # Townes-Brocks syndrome
    "Wilms",          # Wilms tumor
    "Tumoral",        # Tumoral calcinosis
    "Nephrogenic",    # Nephrogenic diabetes insipidus
    "Hyperuricemic",  # Hyperuricemic nephropathy
    "Hypocalcuric",   # Hypocalcuric hypercalcemia
    "Sensorineural",  # Sensorineural hearing loss
    "Short-rib",      # Short-rib thoracic dysplasia
}

# Generic biological/molecular terms
GENERIC_BIOLOGICAL_TERMS = {
    "ATPase",         # Generic enzyme class
    "kinase",         # Generic enzyme class
    "enzyme",         # Generic term
    "factor",         # Generic term
    "regulator",      # Generic term
    "transport",      # Generic function
    "transporter",    # Generic function
    "channel",        # Generic function
    "receptor",       # Generic function
    "protein",        # Generic term
    "domain",         # Protein domain
    "matrix",         # Extracellular matrix
    "member",         # Family member
    "subfamily",      # Gene subfamily
    "family",         # Gene family
    "group",          # Generic group
    "complex",        # Protein complex
    "subunit",        # Protein subunit
    "chain",          # Protein chain
}

# Descriptive and functional terms
DESCRIPTIVE_TERMS = {
    "cation",         # Ion type
    "anion",          # Ion type
    "containing",     # Descriptive word
    "gated",          # Channel type
    "sensitive",      # Functional description
    "dependent",      # Functional description
    "independent",    # Functional description
    "frame",          # Reading frame
    "diphosphate",    # Chemical compound
    "disease",        # Generic term
    "leucine",        # Amino acid
    "lysosomal",      # Cellular compartment
    "mitochondrial",  # Cellular compartment
    "nuclear",        # Cellular compartment
    "cytoplasmic",    # Cellular compartment
    "membrane",       # Cellular structure
    "binding",        # Functional description
    "associated",     # Functional description
    "related",        # Functional description
    "like",           # Similarity descriptor
    "type",           # Classification
    "variant",        # Genetic variant
    "isoform",        # Protein isoform
}

# Medical/clinical terms
MEDICAL_CLINICAL_TERMS = {
    "cramps",         # Clinical symptom
    "segmental",      # Anatomical descriptor
    "sensoryneural",  # Medical term (typo variant)
    "hereditary",     # Inheritance pattern
    "congenital",     # Timing descriptor
    "progressive",    # Disease progression
    "chronic",        # Disease duration
    "acute",          # Disease duration
    "syndrome",       # Medical classification
    "disorder",       # Medical classification
    "deficiency",     # Medical condition
    "dysfunction",    # Medical condition
}

# Common words and artifacts
COMMON_WORDS = {
    "the",            # Article
    "and",            # Conjunction
    "or",             # Conjunction
    "of",             # Preposition
    "in",             # Preposition
    "with",           # Preposition
    "by",             # Preposition
    "for",            # Preposition
    "from",           # Preposition
    "to",             # Preposition
    "Description",    # Document artifact
    "Figure",         # Document artifact
    "Table",          # Document artifact
    "Supplemental",   # Document artifact
    "Additional",     # Document artifact
}

# Gene name aliases that should be mapped (not filtered)
GENE_ALIASES = {
    "actinin-4": "ACTN4",
    "angiotensinogen": "AGT",
    "cubilin": "CUBN",
    "Cubilin": "CUBN",
    "barttin": "BSND",
    "cystinosin": "CTNS",
    "inversin": "INVS",
    "Inversin": "INVS",
    "nephrin": "NPHS1",
    "Nephrin": "NPHS1",
    "podocin": "NPHS2",
    "Podocin": "NPHS2",
    "Renin": "REN",
    "renine": "REN",
    "uromodulin": "UMOD",
    "Uromodulin": "UMOD",
    "lysozyme": "LYZ",
    "thrombomodulin": "THBD",
    "nephrocystin-1": "NPHP1",
    "nephrocystin-3": "NPHP3",
    "RPGRIP1-like": "RPGRIP1L",
    "nephroretinin": "NPHP4",
    "Folliculin": "FLCN",
    "dynein": "DYNC2H1",  # Most common dynein in kidney genetics
}

# Combine all filter sets
FILTER_TERMS = (
    DISEASE_SYNDROME_NAMES |
    GENERIC_BIOLOGICAL_TERMS |
    DESCRIPTIVE_TERMS |
    MEDICAL_CLINICAL_TERMS |
    COMMON_WORDS
)

def should_filter_gene(gene_symbol: str) -> bool:
    """
    Check if a gene symbol should be filtered out as a false positive.
    
    Args:
        gene_symbol: The gene symbol to check
        
    Returns:
        True if the symbol should be filtered out, False otherwise
    """
    # Direct match (case-insensitive)
    if gene_symbol.lower() in {term.lower() for term in FILTER_TERMS}:
        return True
    
    # Check for very short terms (likely artifacts)
    if len(gene_symbol) <= 2:
        return True
    
    # Check for terms that are clearly not genes
    if gene_symbol.lower().endswith(('ase', 'ing', 'tion', 'ment')):
        # But don't filter legitimate gene names ending in 'ase'
        known_ases = {'ALOXE3', 'PPARGC1A', 'CYP2D6'}  # Add more as needed
        if gene_symbol.upper() not in known_ases:
            return True
    
    return False

def clean_gene_symbol(gene_symbol: str) -> str:
    """
    Clean a gene symbol by applying alias mappings or other corrections.
    
    Args:
        gene_symbol: The gene symbol to clean
        
    Returns:
        Cleaned/mapped gene symbol or original if no mapping needed
    """
    # Check for direct alias mapping
    if gene_symbol in GENE_ALIASES:
        return GENE_ALIASES[gene_symbol]
    
    # Remove common prefixes/suffixes that might be extraction artifacts
    cleaned = gene_symbol.strip('.,;:()[]{}"\'-')
    
    # Remove common suffixes that indicate description rather than gene names
    for suffix in ['-positive', '-negative', '-dependent', '-independent', '-like']:
        if cleaned.lower().endswith(suffix):
            cleaned = cleaned[:-len(suffix)]
            break
    
    return cleaned if cleaned else gene_symbol

def get_filter_reason(gene_symbol: str) -> str:
    """
    Get the reason why a gene symbol is being filtered.
    
    Args:
        gene_symbol: The gene symbol to check
        
    Returns:
        String describing why the symbol is filtered, or empty if not filtered
    """
    symbol_lower = gene_symbol.lower()
    
    if symbol_lower in {term.lower() for term in DISEASE_SYNDROME_NAMES}:
        return "Disease/syndrome name"
    elif symbol_lower in {term.lower() for term in GENERIC_BIOLOGICAL_TERMS}:
        return "Generic biological term"
    elif symbol_lower in {term.lower() for term in DESCRIPTIVE_TERMS}:
        return "Descriptive/functional term"
    elif symbol_lower in {term.lower() for term in MEDICAL_CLINICAL_TERMS}:
        return "Medical/clinical term"
    elif symbol_lower in {term.lower() for term in COMMON_WORDS}:
        return "Common word/artifact"
    elif len(gene_symbol) <= 2:
        return "Too short (likely artifact)"
    elif symbol_lower.endswith(('ase', 'ing', 'tion', 'ment')):
        return "Descriptive suffix"
    
    return ""

def get_alias_mapping(gene_symbol: str) -> str:
    """
    Get the HGNC-approved symbol for a gene alias.
    
    Args:
        gene_symbol: The gene symbol to map
        
    Returns:
        HGNC-approved symbol if mapping exists, original symbol otherwise
    """
    return GENE_ALIASES.get(gene_symbol, gene_symbol)