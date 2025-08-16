"""
Update percentiles for each source's evidence records

This matches kidney-genetics-v1 where each source stores source_count_percentile
"""

import logging
from typing import Any

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.gene import GeneEvidence

logger = logging.getLogger(__name__)


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
    stats = {
        "source": source_name,
        "records_processed": 0,
        "percentiles_updated": 0,
    }
    
    # Get all evidence for this source
    evidence_records = (
        db.query(GeneEvidence)
        .filter(GeneEvidence.source_name == source_name)
        .all()
    )
    
    if not evidence_records:
        logger.warning(f"No evidence records found for source: {source_name}")
        return stats
    
    logger.info(f"Calculating percentiles for {len(evidence_records)} {source_name} records")
    
    # Extract counts based on source type
    gene_counts = []
    for evidence in evidence_records:
        count = _get_count_for_evidence(evidence)
        gene_counts.append((evidence, count))
    
    # Sort by count for ranking
    gene_counts.sort(key=lambda x: x[1])
    n = len(gene_counts)
    
    # Calculate percentiles using rank with average tie handling
    # This matches R's rank(ties.method = "average") / n()
    count_groups = {}
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
            stats["records_processed"] += 1
            
            # Add percentile to evidence_data
            if evidence.evidence_data is None:
                evidence.evidence_data = {}
            
            evidence.evidence_data["source_count"] = count
            evidence.evidence_data["source_count_percentile"] = percentile
            
            # Mark as modified for SQLAlchemy to detect JSONB change
            db.add(evidence)
            stats["percentiles_updated"] += 1
            
        current_rank += num_ties
    
    # Commit the updates
    db.commit()
    
    logger.info(
        f"Updated percentiles for {source_name}: "
        f"{stats['percentiles_updated']} records updated"
    )
    
    return stats


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
        return data.get("publication_count", len(data.get("pmids", [])))
        
    elif evidence.source_name == "Literature":
        # Count references
        return len(data.get("references", []))
        
    else:
        # Default: try to count common fields
        return (
            len(data.get("pmids", [])) +
            len(data.get("references", [])) +
            len(data.get("items", []))
        )


def update_all_source_percentiles(db: Session) -> dict[str, Any]:
    """Update percentiles for all sources
    
    Returns:
        Statistics about the update
    """
    # Get unique source names
    sources = db.query(GeneEvidence.source_name).distinct().all()
    source_names = [s[0] for s in sources]
    
    logger.info(f"Updating percentiles for {len(source_names)} sources: {source_names}")
    
    all_stats = {
        "sources_updated": 0,
        "total_records_processed": 0,
        "source_details": {},
    }
    
    for source_name in source_names:
        stats = update_source_percentiles(db, source_name)
        all_stats["sources_updated"] += 1
        all_stats["total_records_processed"] += stats["records_processed"]
        all_stats["source_details"][source_name] = stats
    
    logger.info(
        f"Percentile update complete: {all_stats['sources_updated']} sources, "
        f"{all_stats['total_records_processed']} records processed"
    )
    
    return all_stats