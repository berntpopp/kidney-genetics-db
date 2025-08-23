"""
Evidence aggregation module

Combines evidence from multiple sources and creates curation records.
Scoring is handled by PostgreSQL views, not Python code.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import Gene, GeneCuration, GeneEvidence

logger = get_logger(__name__)


def update_all_curations(db: Session) -> dict[str, Any]:
    """
    Update gene curations with aggregated evidence data.

    NOTE: Evidence scoring is handled by PostgreSQL views, not this function.
    This function only aggregates evidence metadata.

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    logger.sync_info("Starting gene curation update (evidence aggregation only)")

    stats = {
        "genes_processed": 0,
        "curations_created": 0,
        "curations_updated": 0,
        "started_at": datetime.now(timezone.utc),
    }

    # Get all genes with evidence
    genes_with_evidence = db.query(Gene).join(GeneEvidence).distinct().all()

    logger.sync_info("Processing genes with evidence", gene_count=len(genes_with_evidence))

    for gene in genes_with_evidence:
        stats["genes_processed"] += 1

        # Get all evidence for this gene
        evidence_records = db.query(GeneEvidence).filter(GeneEvidence.gene_id == gene.id).all()

        # Aggregate evidence metadata
        evidence_data = _aggregate_evidence_metadata(evidence_records)

        # Get or create curation record
        curation = db.query(GeneCuration).filter(GeneCuration.gene_id == gene.id).first()

        if curation:
            # Update existing curation
            _update_curation_with_evidence(curation, evidence_data)
            stats["curations_updated"] += 1
        else:
            # Create new curation
            curation = GeneCuration(gene_id=gene.id, **evidence_data)
            db.add(curation)
            stats["curations_created"] += 1

    db.commit()

    stats["completed_at"] = datetime.now(timezone.utc)
    stats["duration"] = (stats["completed_at"] - stats["started_at"]).total_seconds()

    logger.sync_info(
        "Curation update complete",
        curations_created=stats['curations_created'],
        curations_updated=stats['curations_updated'],
        duration_seconds=stats['duration']
    )

    return stats


def _aggregate_evidence_metadata(evidence_records: list[GeneEvidence]) -> dict[str, Any]:
    """
    Aggregate evidence metadata from all sources for a gene.

    NOTE: This does NOT calculate scores - that's handled by PostgreSQL views.

    Args:
        evidence_records: List of evidence records for a gene

    Returns:
        Dictionary with aggregated metadata
    """
    # Count evidence by source
    evidence_count = len(evidence_records)
    source_count = len({record.source_name for record in evidence_records})

    # Aggregate arrays from each source
    panelapp_panels = []
    literature_refs = []
    hpo_terms = []
    pubtator_pmids = []
    omim_data = {}
    clinvar_data = {}

    for evidence in evidence_records:
        evidence_data = evidence.evidence_data or {}

        if evidence.source_name == "PanelApp":
            panelapp_panels.extend(evidence_data.get("panels", []))

        elif evidence.source_name == "HPO":
            hpo_terms.extend(evidence_data.get("phenotypes", []))

        elif evidence.source_name == "PubTator":
            pubtator_pmids.extend(evidence_data.get("pmids", []))

        elif evidence.source_name == "HPO":
            omim_data.update(evidence_data)

        elif evidence.source_name == "ClinVar":
            clinvar_data.update(evidence_data)

    # Remove duplicates for simple lists
    unique_literature_refs = list(set(literature_refs)) if literature_refs else []
    unique_hpo_terms = list(set(hpo_terms)) if hpo_terms else []
    unique_pubtator_pmids = list(set(pubtator_pmids)) if pubtator_pmids else []

    # For panels (list of dicts), convert to strings for storage
    # Format: "PanelName (ID:version)"
    unique_panels = []
    seen_panels = set()
    for panel in panelapp_panels:
        if isinstance(panel, dict):
            panel_str = f"{panel.get('name', 'Unknown')} (ID:{panel.get('id', '?')} v{panel.get('version', '?')})"
        else:
            panel_str = str(panel)
        if panel_str not in seen_panels:
            seen_panels.add(panel_str)
            unique_panels.append(panel_str)

    return {
        "evidence_count": evidence_count,
        "source_count": source_count,
        "panelapp_panels": unique_panels,
        "literature_refs": unique_literature_refs,
        "hpo_terms": unique_hpo_terms,
        "pubtator_pmids": unique_pubtator_pmids,
        "omim_data": omim_data,
        "clinvar_data": clinvar_data,
        # NOTE: evidence_score is calculated by PostgreSQL views, not here
        "evidence_score": 0.0,  # Placeholder - real scores come from views
        "classification": None,  # Will be set by curation workflow
    }


def _update_curation_with_evidence(curation: GeneCuration, evidence_data: dict[str, Any]) -> None:
    """
    Update existing curation record with new evidence data.

    Args:
        curation: Existing curation record
        evidence_data: New evidence data to merge
    """
    # Update metadata (preserve existing classification if any)
    existing_classification = curation.classification

    for key, value in evidence_data.items():
        if key != "classification" or existing_classification is None:
            setattr(curation, key, value)

    # Preserve manual classification if it exists
    if existing_classification:
        curation.classification = existing_classification

    curation.updated_at = datetime.now(timezone.utc)
