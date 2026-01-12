"""
Update percentiles for each source's evidence records

This matches kidney-genetics-v1 where each source stores source_count_percentile
"""

from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.gene import GeneEvidence

logger = get_logger(__name__)


def update_source_percentiles(db: Session, source_name: str) -> dict[str, Any]:
    """Update percentiles for all evidence records from a source

    This adds source_count_percentile to each evidence_data JSONB,
    matching the R implementation's normalize_percentile() function.

    Args:
        db: Database session
        source_name: Name of the source to update

    Returns:
        Statistics about the update
    """
    records_processed = 0
    percentiles_updated = 0

    # Get all evidence for this source
    evidence_records = db.query(GeneEvidence).filter(GeneEvidence.source_name == source_name).all()

    if not evidence_records:
        logger.sync_warning(f"No evidence records found for source: {source_name}")
        return {
            "source": source_name,
            "records_processed": records_processed,
            "percentiles_updated": percentiles_updated,
        }

    logger.sync_info(f"Calculating percentiles for {len(evidence_records)} {source_name} records")

    # Extract counts based on source type
    gene_counts: list[tuple[GeneEvidence, int]] = []
    for evidence in evidence_records:
        count = _get_count_for_evidence(evidence)
        gene_counts.append((evidence, count))

    # Sort by count for ranking
    gene_counts.sort(key=lambda x: x[1])
    n = len(gene_counts)

    # Calculate percentiles using rank with average tie handling
    # This matches R's rank(ties.method = "average") / n()
    count_groups: dict[int, list[GeneEvidence]] = {}
    for evidence, count in gene_counts:
        if count not in count_groups:
            count_groups[count] = []
        count_groups[count].append(evidence)

    # Assign percentiles with average rank for ties
    current_rank = 0
    for count in sorted(count_groups.keys()):
        evidence_list = count_groups[count]
        num_ties = len(evidence_list)

        # Average rank for this group
        ranks = list(range(current_rank + 1, current_rank + num_ties + 1))
        avg_rank = sum(ranks) / num_ties

        # Convert to percentile (0-1)
        percentile = avg_rank / n

        # Update each evidence record
        for evidence in evidence_list:
            records_processed += 1

            # Add percentile to evidence_data
            if evidence.evidence_data is None:
                evidence.evidence_data = {}

            evidence.evidence_data["source_count"] = count
            evidence.evidence_data["source_count_percentile"] = percentile

            # Mark as modified for SQLAlchemy to detect JSONB change
            db.add(evidence)
            percentiles_updated += 1

        current_rank += num_ties

    # Commit the updates
    db.commit()

    logger.sync_info(
        "Updated percentiles",
        source_name=source_name,
        percentiles_updated=percentiles_updated,
    )

    return {
        "source": source_name,
        "records_processed": records_processed,
        "percentiles_updated": percentiles_updated,
    }


def _get_count_for_evidence(evidence: GeneEvidence) -> int:
    """Extract the relevant count from evidence data

    Args:
        evidence: GeneEvidence record

    Returns:
        Count value for percentile calculation
    """
    data = evidence.evidence_data or {}

    if evidence.source_name == "PanelApp":
        # Count number of panels
        return len(data.get("panels", []))

    elif evidence.source_name == "HPO":
        # Count phenotypes + diseases
        phenotypes = len(data.get("phenotypes", []))
        diseases = len(data.get("disease_associations", []))
        return phenotypes + diseases

    elif evidence.source_name == "PubTator":
        # Use publication_count if available, else count pmids
        pub_count = data.get("publication_count")
        if pub_count is not None:
            return int(pub_count)
        return len(data.get("pmids", []))

    elif evidence.source_name == "DiagnosticPanels":
        # Count panels
        panel_count = data.get("panel_count")
        if panel_count is not None:
            return int(panel_count)
        return len(data.get("panels", []))

    else:
        # Default: try to count common fields
        return (
            len(data.get("pmids", []))
            + len(data.get("references", []))
            + len(data.get("items", []))
        )


def update_all_source_percentiles(db: Session) -> dict[str, Any]:
    """Update percentiles for all sources

    Returns:
        Statistics about the update
    """
    # Get unique source names
    sources = db.query(GeneEvidence.source_name).distinct().all()
    source_names = [s[0] for s in sources]

    logger.sync_info(f"Updating percentiles for {len(source_names)} sources: {source_names}")

    sources_updated = 0
    total_records_processed = 0
    source_details: dict[str, dict[str, Any]] = {}

    for source_name in source_names:
        stats = update_source_percentiles(db, source_name)
        sources_updated += 1
        total_records_processed += stats["records_processed"]
        source_details[source_name] = stats

    logger.sync_info(
        "Percentile update complete",
        sources_updated=sources_updated,
        total_records_processed=total_records_processed,
    )

    return {
        "sources_updated": sources_updated,
        "total_records_processed": total_records_processed,
        "source_details": source_details,
    }
