"""Shared evidence data transformation utilities.

Extracted from genes.py to centralize JSON:API evidence formatting.
"""

from typing import Any


def transform_evidence_to_jsonapi(
    evidence_list: list[Any],
    gene_id: int,
    normalized_scores: dict[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Transform evidence records to JSON:API format.

    Args:
        evidence_list: List of evidence ORM objects.
        gene_id: ID of the parent gene.
        normalized_scores: Optional dict mapping evidence_id to score.

    Returns:
        List of JSON:API-formatted evidence dicts.
    """
    scores = normalized_scores or {}
    evidence_data = []
    for e in evidence_list:
        evidence_data.append(
            {
                "type": "evidence",
                "id": str(e.id),
                "attributes": {
                    "source_name": e.source_name,
                    "source_detail": e.source_detail,
                    "evidence_data": e.evidence_data,
                    "evidence_date": (e.evidence_date.isoformat() if e.evidence_date else None),
                    "created_at": (e.created_at.isoformat() if e.created_at else None),
                    "normalized_score": scores.get(e.id, 0.0),
                },
                "relationships": {"gene": {"data": {"type": "genes", "id": str(gene_id)}}},
            }
        )
    return evidence_data
