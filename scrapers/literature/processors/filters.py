"""Common filters for excluding non-gene terms from extraction."""

# Disease and syndrome abbreviations that are not gene symbols
DISEASE_TERMS = {
    "ADPKD",  # Autosomal Dominant Polycystic Kidney Disease
    "ARPKD",  # Autosomal Recessive Polycystic Kidney Disease
    "ADTKD",  # Autosomal Dominant Tubulointerstitial Kidney Disease
    "CAKUT",  # Congenital Anomalies of Kidney and Urinary Tract
    "NPHP",  # Nephronophthisis (though NPHP1-20 are valid genes)
    "JBTS",  # Joubert Syndrome
    "SLSN",  # Senior-Loken Syndrome
    "FSGS",  # Focal Segmental Glomerulosclerosis
    "SRNS",  # Steroid-Resistant Nephrotic Syndrome
    "SSNS",  # Steroid-Sensitive Nephrotic Syndrome
    "HUS",  # Hemolytic Uremic Syndrome
    "aHUS",  # Atypical Hemolytic Uremic Syndrome
    "TMA",  # Thrombotic Microangiopathy
    "CKD",  # Chronic Kidney Disease
    "ESKD",  # End-Stage Kidney Disease
    "ESRD",  # End-Stage Renal Disease
    "RTA",  # Renal Tubular Acidosis
    "NDI",  # Nephrogenic Diabetes Insipidus
    "CDI",  # Central Diabetes Insipidus
    "GN",  # Glomerulonephritis
    "MPGN",  # Membranoproliferative Glomerulonephritis
    "IgAN",  # IgA Nephropathy
    "MCD",  # Minimal Change Disease
    "MCNS",  # Minimal Change Nephrotic Syndrome
    "DMS",  # Diffuse Mesangial Sclerosis
    "CNS",  # Congenital Nephrotic Syndrome
    "BOR",  # Branchio-Oto-Renal syndrome
    "BORS",  # Branchio-Oto-Renal syndrome
    "CHARGE",  # CHARGE syndrome
    "VACTERL",  # VACTERL association
}

# Clinical and descriptive terms
CLINICAL_TERMS = {
    "HEREDITARY",
    "ISOLATED",
    "SYNDROMIC",
    "RARE",
    "COMMON",
    "VARIANT",
    "MUTATION",
    "DELETION",
    "DUPLICATION",
    "TUBULOPATHIES",
    "GLOMERULOPATHIES",
    "CILIOPATHIES",
    "NEPHROPATHIES",
    "DOMINANT",
    "RECESSIVE",
    "AUTOSOMAL",
    "XLINKED",
    "MATERNAL",
    "PATERNAL",
    "SPORADIC",
    "FAMILIAL",
    "CONGENITAL",
    "ACQUIRED",
    "IDIOPATHIC",
    "GENETIC",
    "MONOGENIC",
    "POLYGENIC",
    "MULTIFACTORIAL",
}

# Database and system identifiers
DATABASE_TERMS = {
    "OMIM",  # Online Mendelian Inheritance in Man
    "HGNC",  # HUGO Gene Nomenclature Committee (when standalone)
    "NCBI",  # National Center for Biotechnology Information
    "ENSEMBL",  # Ensembl
    "UNIPROT",  # UniProt
    "REFSEQ",  # RefSeq
    "GENBANK",  # GenBank
    "KEGG",  # Kyoto Encyclopedia of Genes and Genomes
    "GO",  # Gene Ontology
    "HPO",  # Human Phenotype Ontology
    "ORPHA",  # Orphanet
    "MONDO",  # Mondo Disease Ontology
    "DOID",  # Disease Ontology
    "PUBMED",  # PubMed
    "DOI",  # Digital Object Identifier
}

# Common false positives
FALSE_POSITIVES = {
    "TABLE",
    "FIGURE",
    "SUPPLEMENTARY",
    "SUPPLEMENTAL",
    "GENE",
    "GENES",
    "PANEL",
    "PANELS",
    "TOTAL",
    "NA",
    "NULL",
    "NAME",
    "SYMBOL",
    "ID",
    "UNKNOWN",
    "OTHER",
    "NONE",
    "ALL",
    "ANY",
    "TEST",
    "ANALYSIS",
    "STUDY",
    "COHORT",
    "PATIENT",
    "PATIENTS",
    "CASE",
    "CASES",
    "CONTROL",
    "CONTROLS",
    "NORMAL",
    "ABNORMAL",
    "POSITIVE",
    "NEGATIVE",
    "V1",
    "V2",
    "V3",  # Version indicators
    "I",
    "II",
    "III",
    "IV",
    "V",  # Roman numerals (when standalone)
}

# Laboratory and clinical abbreviations
LAB_TERMS = {
    "PCR",
    "NGS",
    "WES",
    "WGS",
    "CNV",
    "SNV",
    "SNP",
    "INDEL",
    "VUS",
    "VOUS",
    "LOF",
    "GOF",
    "UTR",
    "CDS",
    "ACMG",
    "VEP",
    "CADD",
    "SIFT",
    "MAF",
    "VAF",
    "AD",
    "AR",
    "XL",
    "MT",
}

# Combine all exclusion terms
ALL_EXCLUSION_TERMS = DISEASE_TERMS | CLINICAL_TERMS | DATABASE_TERMS | FALSE_POSITIVES | LAB_TERMS


def should_exclude_symbol(symbol: str) -> bool:
    """
    Check if a symbol should be excluded as a non-gene term.

    Args:
        symbol: The symbol to check

    Returns:
        True if the symbol should be excluded, False otherwise
    """
    # Check exact match (case-insensitive)
    if symbol.upper() in ALL_EXCLUSION_TERMS:
        return True

    # Special case: NPHP followed by numbers is a valid gene (NPHP1, NPHP2, etc.)
    if symbol.upper().startswith("NPHP") and len(symbol) > 4 and symbol[4:].isdigit():
        return False

    # Special case: BBS followed by numbers is a valid gene (BBS1, BBS2, etc.)
    if symbol.upper().startswith("BBS") and len(symbol) > 3 and symbol[3:].isdigit():
        return False

    # Check if it's just a number or roman numeral
    if symbol.isdigit() or symbol in [
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "IX",
        "X",
    ]:
        return True

    return False


def clean_and_validate_symbol(symbol: str) -> str:
    """
    Clean and validate a gene symbol, returning empty string if invalid.

    Args:
        symbol: The symbol to clean and validate

    Returns:
        Cleaned symbol or empty string if invalid
    """
    # Basic cleaning
    symbol = symbol.strip()

    # Remove common suffixes that aren't part of gene names
    for suffix in ["_1", "_2", "_3", "-like", "-related"]:
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]

    # Check if should be excluded
    if should_exclude_symbol(symbol):
        return ""

    # Basic validation
    if not symbol or len(symbol) < 2 or len(symbol) > 15:
        return ""

    # Should start with a letter (except for special cases like 3'UTR genes)
    if not symbol[0].isalpha() and not symbol[0].isdigit():
        return ""

    return symbol
