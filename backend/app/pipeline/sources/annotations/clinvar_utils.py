"""
Pure utility functions for parsing ClinVar variant_summary.txt data.

All functions are stateless with no DB/session dependencies,
making them easy to test in isolation.
"""

import re
from typing import Any

# Pre-compiled regexes
_PROTEIN_CHANGE_RE = re.compile(r"\((p\..*?)\)")
_PROTEIN_POSITION_RE = re.compile(r"[A-Za-z]{3}(\d+)")
_SPLICE_CANONICAL_RE = re.compile(r"c\.\d+[+-][12][^\d]|c\.\d+[+-][12]$")
_SPLICE_INTRONIC_RE = re.compile(r"c\.\d+[+-]\d+")

# Three-letter amino acid codes (for missense detection)
_AMINO_ACIDS_3 = {
    "Ala",
    "Arg",
    "Asn",
    "Asp",
    "Cys",
    "Gln",
    "Glu",
    "Gly",
    "His",
    "Ile",
    "Leu",
    "Lys",
    "Met",
    "Phe",
    "Pro",
    "Ser",
    "Thr",
    "Trp",
    "Tyr",
    "Val",
    "Sec",
    "Pyl",
}

# Missense pattern: p.Xxx###Yyy where Xxx and Yyy are amino acids
_MISSENSE_RE = re.compile(r"p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})")


def parse_protein_change(name: str) -> str:
    """Extract p.Xxx###Yyy protein change from HGVS Name.

    Args:
        name: Full HGVS notation string (e.g. "NM_000297.4:c.12616C>T (p.Arg4206Trp)")

    Returns:
        Protein change string (e.g. "p.Arg4206Trp") or empty string if not found.
    """
    if not name:
        return ""
    match = _PROTEIN_CHANGE_RE.search(name)
    return match.group(1) if match else ""


def parse_protein_position(protein_change: str) -> int | None:
    """Extract numeric position from HGVS protein change notation.

    Args:
        protein_change: e.g. "p.Arg4206Trp", "p.Gly1234*", "p.Ter1234Cys"

    Returns:
        Integer position or None if cannot be parsed.
    """
    if not protein_change:
        return None
    # Strip leading "p." for matching
    cleaned = protein_change
    if cleaned.startswith("p."):
        cleaned = cleaned[2:]
    match = _PROTEIN_POSITION_RE.search(cleaned)
    if match:
        return int(match.group(1))
    return None


def infer_effect_category(name: str) -> str:
    """Infer variant effect category from HGVS Name notation.

    Rules (in priority order):
    - p.*Ter* (not ext) → truncating (nonsense)
    - p.*fs* → truncating (frameshift)
    - p.Xxx###Yyy (Xxx≠Yyy, Yyy≠Ter) → missense
    - del/dup/ins without fs → inframe
    - p.*= → synonymous
    - c.NNN+1/+2/-1/-2 → splice_region (canonical)
    - c.NNN+N/-N (N>2) → intronic
    - anything else → other

    Args:
        name: Full HGVS notation string.

    Returns:
        Effect category string.
    """
    if not name:
        return "other"

    protein = parse_protein_change(name)

    # Check protein-level changes first
    if protein:
        # Frameshift (check before nonsense since fs can include Ter)
        if "fs" in protein:
            return "truncating"

        # Nonsense: contains Ter but not ext (readthrough/extension)
        if "Ter" in protein and "ext" not in protein:
            # p.Xxx###Ter or p.Ter###Xxx (stop gain)
            # But not p.Ter###XxxextTer### (extension)
            return "truncating"

        # Stop notation with *
        if "*" in protein and "ext" not in protein and "fs" not in protein:
            return "truncating"

        # Synonymous: p.Xxx###= (silent mutation)
        if protein.endswith("="):
            return "synonymous"

        # Missense: p.Xxx###Yyy where both are amino acids and different
        m = _MISSENSE_RE.search(protein)
        if m:
            aa_from, _, aa_to = m.group(1), m.group(2), m.group(3)
            if aa_from != aa_to and aa_to != "Ter":
                return "missense"

    # Check for inframe indels (del/dup/ins without fs in protein)
    if protein and ("del" in protein or "dup" in protein or "ins" in protein):
        if "fs" not in protein:
            return "inframe"

    # Splice site detection from cDNA notation
    if _SPLICE_CANONICAL_RE.search(name):
        return "splice_region"

    if _SPLICE_INTRONIC_RE.search(name):
        return "intronic"

    # Check for genomic-level del/dup/ins (no protein change available)
    if not protein:
        for pattern in ("del", "dup", "ins"):
            if pattern in name.lower():
                return "inframe"

    return "other"


def infer_molecular_consequences(name: str, effect_category: str) -> list[str]:
    """Map effect_category to Sequence Ontology term labels.

    Args:
        name: HGVS notation (used for splice sub-typing).
        effect_category: Result from infer_effect_category().

    Returns:
        List of SO term label strings.
    """
    if effect_category == "truncating":
        protein = parse_protein_change(name)
        if protein and "fs" in protein:
            return ["frameshift variant"]
        return ["nonsense"]

    if effect_category == "missense":
        return ["missense variant"]

    if effect_category == "inframe":
        return ["inframe_indel"]

    if effect_category == "synonymous":
        return ["synonymous variant"]

    if effect_category == "splice_region":
        # Distinguish donor vs acceptor
        if re.search(r"c\.\d+\+[12]([^\d]|$)", name):
            return ["splice donor variant"]
        if re.search(r"c\.\d+-[12]([^\d]|$)", name):
            return ["splice acceptor variant"]
        return ["splice donor variant"]

    if effect_category == "intronic":
        return ["intron variant"]

    return ["other"]


def map_classification(clinical_significance: str) -> str:
    """Map ClinicalSignificance text to a normalized category.

    Args:
        clinical_significance: Raw text from ClinVar (e.g. "Pathogenic",
            "Pathogenic/Likely pathogenic", "Uncertain significance; other").

    Returns:
        Normalized category string.
    """
    if not clinical_significance:
        return "not_provided"

    sig = clinical_significance.lower().strip()

    # Handle combined classifications with "/" or ";"
    # "Pathogenic/Likely pathogenic" → pathogenic
    if "conflicting" in sig:
        return "conflicting"

    if "pathogenic" in sig:
        if "likely" in sig and "pathogenic/likely" not in sig:
            return "likely_pathogenic"
        if "benign" in sig:
            # "Pathogenic; Likely benign" or similar mixed → conflicting
            return "conflicting"
        if "likely pathogenic" == sig or (
            "likely" in sig and "pathogenic" in sig and "/" not in sig
        ):
            return "likely_pathogenic"
        return "pathogenic"

    if "benign" in sig:
        if "likely" in sig:
            return "likely_benign"
        return "benign"

    if "uncertain" in sig or "vus" in sig:
        return "vus"

    if "not provided" in sig or sig == "-" or not sig:
        return "not_provided"

    return "other"


def map_review_confidence(review_status: str, confidence_levels: dict[str, int]) -> int:
    """Map ReviewStatus text to a 0-4 star confidence level.

    Args:
        review_status: Raw ReviewStatus text from ClinVar.
        confidence_levels: Mapping of status text → star level.

    Returns:
        Integer star level (0-4).
    """
    if not review_status or review_status == "-":
        return 0
    return confidence_levels.get(review_status.lower().strip(), 0)


def format_accession(variation_id: str) -> str:
    """Format a VariationID into a ClinVar VCV accession.

    Args:
        variation_id: Numeric string (e.g. "12345").

    Returns:
        Formatted accession (e.g. "VCV000012345").
    """
    try:
        return f"VCV{int(variation_id):09d}"
    except (ValueError, TypeError):
        return f"VCV{variation_id}"


def _safe_int(val: str) -> int | None:
    """Convert string to int, returning None for non-numeric values."""
    if not val or val == "-" or val == "na":
        return None
    try:
        return int(val)
    except ValueError:
        return None


class GeneAccumulator:
    """Incrementally accumulate variant statistics for one gene.

    Memory-efficient alternative to collecting all variant dicts and then
    calling ``_aggregate_variants()``.  Detail lists (protein_variants,
    genomic_variants) are capped at *max_detail* to bound JSONB size.

    Usage::

        acc = GeneAccumulator(confidence_levels, max_detail=200)
        for variant in stream:
            acc.add_variant(variant)
        stats = acc.finalize()
    """

    __slots__ = (
        "total_count",
        "pathogenic_count",
        "likely_pathogenic_count",
        "vus_count",
        "benign_count",
        "likely_benign_count",
        "conflicting_count",
        "not_provided_count",
        "high_confidence_count",
        "variant_type_counts",
        "traits_summary",
        "molecular_consequences",
        "consequence_categories",
        "protein_variants",
        "genomic_variants",
        "_confidence_levels",
        "_max_detail",
    )

    _TRUNCATING: frozenset[str] = frozenset({"nonsense", "frameshift variant", "start lost"})
    _SPLICE: frozenset[str] = frozenset(
        {"splice donor variant", "splice acceptor variant", "splice region variant"}
    )

    def __init__(self, confidence_levels: dict[str, int], max_detail: int = 200) -> None:
        self.total_count = 0
        self.pathogenic_count = 0
        self.likely_pathogenic_count = 0
        self.vus_count = 0
        self.benign_count = 0
        self.likely_benign_count = 0
        self.conflicting_count = 0
        self.not_provided_count = 0
        self.high_confidence_count = 0
        self.variant_type_counts: dict[str, int] = {}
        self.traits_summary: dict[str, int] = {}
        self.molecular_consequences: dict[str, int] = {}
        self.consequence_categories: dict[str, int] = {
            "truncating": 0,
            "missense": 0,
            "inframe": 0,
            "splice_region": 0,
            "regulatory": 0,
            "intronic": 0,
            "synonymous": 0,
            "other": 0,
        }
        self.protein_variants: list[dict[str, Any]] = []
        self.genomic_variants: list[dict[str, Any]] = []
        self._confidence_levels = confidence_levels
        self._max_detail = max_detail

    # ------------------------------------------------------------------ #

    def add_variant(self, variant: dict[str, Any]) -> None:
        """Incorporate one parsed variant dict into running totals.

        Replicates the per-variant logic from
        ``ClinVarAnnotationSource._aggregate_variants`` so results are
        identical when consumed via ``finalize()``.
        """
        self.total_count += 1
        classification = variant["classification"].lower()

        # --- Classification counting (pathogenic / likely pathogenic) ---
        is_pathogenic = False
        if "pathogenic" in classification:
            is_pathogenic = True
            if "likely" in classification:
                self.likely_pathogenic_count += 1
            elif "/" not in classification:
                self.pathogenic_count += 1
            elif "pathogenic/likely pathogenic" in classification:
                self.pathogenic_count += 1

        # --- Category label for detail dicts ---
        if is_pathogenic:
            category = "likely_pathogenic" if "likely" in classification else "pathogenic"
        elif "benign" in classification:
            category = "likely_benign" if "likely" in classification else "benign"
        elif "uncertain" in classification or "vus" in classification:
            category = "vus"
        elif "conflicting" in classification:
            category = "conflicting"
        else:
            category = "other"

        confidence = self._confidence_levels.get(variant.get("review_status", ""), 0)
        mol_consequences = variant.get("molecular_consequences", [])

        # --- Effect category from molecular consequences ---
        effect_category = "other"
        for conseq in mol_consequences:
            conseq_lower = conseq.lower()
            if conseq_lower in self._TRUNCATING:
                effect_category = "truncating"
                break
            elif conseq_lower in self._SPLICE or "splice" in conseq_lower:
                if effect_category not in ("truncating",):
                    effect_category = "splice_region"
            elif "missense" in conseq_lower:
                if effect_category not in ("truncating", "splice_region"):
                    effect_category = "missense"
            elif "inframe" in conseq_lower:
                if effect_category not in ("truncating", "splice_region", "missense"):
                    effect_category = "inframe"
            elif "synonymous" in conseq_lower:
                if effect_category == "other":
                    effect_category = "synonymous"

        # --- Protein variants (capped) ---
        protein_change = variant.get("protein_change", "")
        position = parse_protein_position(protein_change)
        if position and len(self.protein_variants) < self._max_detail:
            self.protein_variants.append(
                {
                    "position": position,
                    "protein_change": protein_change,
                    "cdna_change": variant.get("cdna_change", ""),
                    "accession": variant.get("accession", ""),
                    "classification": variant.get("classification", ""),
                    "category": category,
                    "effect_category": effect_category,
                    "review_status": variant.get("review_status", ""),
                    "confidence": confidence,
                    "molecular_consequences": mol_consequences,
                    "variant_type": variant.get("variant_type", ""),
                    "title": variant.get("title", ""),
                    "chromosome": variant.get("chromosome"),
                    "genomic_start": variant.get("genomic_start"),
                    "genomic_end": variant.get("genomic_end"),
                }
            )

        # --- Genomic variants (capped) ---
        genomic_start = variant.get("genomic_start")
        if genomic_start is not None and len(self.genomic_variants) < self._max_detail:
            self.genomic_variants.append(
                {
                    "position": position,
                    "protein_change": protein_change,
                    "cdna_change": variant.get("cdna_change", ""),
                    "accession": variant.get("accession", ""),
                    "classification": variant.get("classification", ""),
                    "category": category,
                    "effect_category": effect_category,
                    "review_status": variant.get("review_status", ""),
                    "confidence": confidence,
                    "molecular_consequences": mol_consequences,
                    "variant_type": variant.get("variant_type", ""),
                    "title": variant.get("title", ""),
                    "chromosome": variant.get("chromosome"),
                    "genomic_start": genomic_start,
                    "genomic_end": variant.get("genomic_end"),
                }
            )

        # --- Other classification counts ---
        if not is_pathogenic and "benign" in classification:
            if "likely" in classification:
                self.likely_benign_count += 1
            elif "/" not in classification:
                self.benign_count += 1
        elif "uncertain" in classification or "vus" in classification:
            self.vus_count += 1
        elif "conflicting" in classification:
            self.conflicting_count += 1
        elif "not provided" in classification:
            self.not_provided_count += 1

        # --- High-confidence counting ---
        confidence2 = self._confidence_levels.get(variant["review_status"], 0)
        if confidence2 >= 3:
            self.high_confidence_count += 1

        # --- Variant type ---
        vtype = variant.get("variant_type", "")
        self.variant_type_counts[vtype] = self.variant_type_counts.get(vtype, 0) + 1

        # --- Traits ---
        for trait in variant.get("traits", []):
            name = trait.get("name")
            if name:
                self.traits_summary[name] = self.traits_summary.get(name, 0) + 1

        # --- Molecular consequence counts + consequence categories ---
        for consequence in mol_consequences:
            self.molecular_consequences[consequence] = (
                self.molecular_consequences.get(consequence, 0) + 1
            )
            consequence_lower = consequence.lower()
            if consequence_lower in self._TRUNCATING:
                self.consequence_categories["truncating"] += 1
            elif consequence_lower in self._SPLICE or "splice" in consequence_lower:
                self.consequence_categories["splice_region"] += 1
            elif "missense" in consequence_lower:
                self.consequence_categories["missense"] += 1
            elif "synonymous" in consequence_lower:
                self.consequence_categories["synonymous"] += 1
            elif "inframe" in consequence_lower:
                self.consequence_categories["inframe"] += 1
            elif "UTR" in consequence:
                self.consequence_categories["regulatory"] += 1
            elif "intron" in consequence_lower:
                self.consequence_categories["intronic"] += 1
            else:
                self.consequence_categories["other"] += 1

    # ------------------------------------------------------------------ #

    def finalize(self) -> dict[str, Any]:
        """Return the same stats dict that ``_aggregate_variants()`` produces."""
        total = self.total_count

        top_consequences = sorted(
            self.molecular_consequences.items(), key=lambda x: x[1], reverse=True
        )[:10]
        top_molecular_consequences = [
            {"consequence": c[0], "count": c[1]} for c in top_consequences
        ]

        percentages: dict[str, float] = {}
        if total > 0:
            for cat_name in self.consequence_categories:
                percentages[f"{cat_name}_percentage"] = round(
                    (self.consequence_categories[cat_name] / total) * 100, 1
                )

        top_traits_sorted = sorted(self.traits_summary.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        top_traits = [{"trait": t[0], "count": t[1]} for t in top_traits_sorted]

        high_confidence_percentage = 0.0
        pathogenic_percentage = 0.0
        if total > 0:
            high_confidence_percentage = round((self.high_confidence_count / total) * 100, 1)
            pathogenic_percentage = round(
                ((self.pathogenic_count + self.likely_pathogenic_count) / total) * 100,
                1,
            )

        has_pathogenic = self.pathogenic_count > 0 or self.likely_pathogenic_count > 0

        stats: dict[str, Any] = {
            "total_count": total,
            "pathogenic_count": self.pathogenic_count,
            "likely_pathogenic_count": self.likely_pathogenic_count,
            "vus_count": self.vus_count,
            "benign_count": self.benign_count,
            "likely_benign_count": self.likely_benign_count,
            "conflicting_count": self.conflicting_count,
            "not_provided_count": self.not_provided_count,
            "high_confidence_count": self.high_confidence_count,
            "variant_type_counts": self.variant_type_counts,
            "molecular_consequences": self.molecular_consequences,
            "protein_variants": self.protein_variants,
            "genomic_variants": self.genomic_variants,
            "consequence_categories": self.consequence_categories,
            "top_molecular_consequences": top_molecular_consequences,
            "top_traits": top_traits,
            "high_confidence_percentage": high_confidence_percentage,
            "pathogenic_percentage": pathogenic_percentage,
            "has_pathogenic": has_pathogenic,
        }
        stats.update(percentages)
        return stats


def parse_variant_row(row: dict[str, str], confidence_levels: dict[str, int]) -> dict[str, Any]:
    """Parse one TSV row from variant_summary.txt into a normalized variant dict.

    The output schema matches the structure expected by _aggregate_variants():
    variant_id, accession, title, variant_type, classification, review_status,
    traits, molecular_consequences, chromosome, genomic_start, genomic_end,
    protein_change, cdna_change.

    Args:
        row: Dict with TSV column names as keys.
        confidence_levels: ReviewStatus → star mapping.

    Returns:
        Normalized variant dictionary.
    """
    name = row.get("Name", "")
    clinical_sig = row.get("ClinicalSignificance", "")
    review_status = row.get("ReviewStatus", "")
    variation_id = row.get("VariationID", "")

    protein_change = parse_protein_change(name)
    effect_category = infer_effect_category(name)
    mol_consequences = infer_molecular_consequences(name, effect_category)

    # Parse traits from PhenotypeList (pipe-separated)
    phenotype_list = row.get("PhenotypeList", "")
    traits: list[dict[str, Any]] = []
    if phenotype_list and phenotype_list not in ("-", "not provided", "not specified"):
        for pheno in phenotype_list.split("|"):
            pheno = pheno.strip()
            if pheno and pheno not in ("not provided", "not specified"):
                traits.append({"name": pheno, "omim_id": None, "medgen_id": None})

    # Parse genomic coordinates
    genomic_start = _safe_int(row.get("Start", ""))
    genomic_end = _safe_int(row.get("Stop", ""))

    return {
        "variant_id": variation_id,
        "accession": format_accession(variation_id),
        "title": name,
        "variant_type": row.get("Type", ""),
        "classification": clinical_sig if clinical_sig else "Not classified",
        "review_status": review_status if review_status else "No data",
        "traits": traits,
        "molecular_consequences": mol_consequences,
        "chromosome": row.get("Chromosome", ""),
        "genomic_start": genomic_start,
        "genomic_end": genomic_end,
        "protein_change": protein_change,
        "cdna_change": name,
    }
