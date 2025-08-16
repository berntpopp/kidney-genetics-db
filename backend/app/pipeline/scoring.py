"""
Evidence scoring with percentile normalization

Implements the same scoring approach as kidney-genetics-v1:
1. Normalize each source's counts to percentiles (0-1)
2. Sum percentiles across sources for final score
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.gene import Gene, GeneEvidence

logger = logging.getLogger(__name__)


class PercentileScorer:
    """Calculate percentile-based scores like kidney-genetics-v1"""

    def __init__(self, db: Session):
        """Initialize scorer with database session"""
        self.db = db
        self._percentile_cache = {}

    def calculate_percentiles_for_source(self, source_name: str) -> dict[int, float]:
        """Calculate percentiles for all genes from a source

        Args:
            source_name: Name of the evidence source

        Returns:
            Dictionary mapping gene_id to percentile (0-1)
        """
        if source_name in self._percentile_cache:
            return self._percentile_cache[source_name]

        # Get all evidence for this source
        evidence_records = (
            self.db.query(GeneEvidence)
            .filter(GeneEvidence.source_name == source_name)
            .all()
        )

        if not evidence_records:
            return {}

        # Extract counts based on source type
        gene_counts = []
        for evidence in evidence_records:
            gene_id = evidence.gene_id
            count = self._get_count_for_evidence(evidence)
            gene_counts.append((gene_id, count))

        # Sort by count
        gene_counts.sort(key=lambda x: x[1])

        # Calculate percentiles using rank method "average" for ties
        # This matches R's rank(ties.method = "average") / n()
        n = len(gene_counts)
        percentiles = {}

        # Group by count value for tie handling
        count_groups = {}
        for gene_id, count in gene_counts:
            if count not in count_groups:
                count_groups[count] = []
            count_groups[count].append(gene_id)

        # Assign percentiles with average rank for ties
        current_rank = 0
        for count in sorted(count_groups.keys()):
            gene_ids = count_groups[count]
            num_ties = len(gene_ids)

            # Average rank for this group
            ranks = list(range(current_rank + 1, current_rank + num_ties + 1))
            avg_rank = sum(ranks) / num_ties

            # Convert to percentile (0-1)
            percentile = avg_rank / n

            for gene_id in gene_ids:
                percentiles[gene_id] = percentile

            current_rank += num_ties

        self._percentile_cache[source_name] = percentiles
        return percentiles

    def _get_count_for_evidence(self, evidence: GeneEvidence) -> int:
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
            # Count phenotypes/diseases
            phenotypes = len(data.get("phenotypes", []))
            diseases = len(data.get("disease_associations", []))
            return phenotypes + diseases

        elif evidence.source_name == "PubTator":
            # Count publications
            return data.get("publication_count", len(data.get("pmids", [])))

        elif evidence.source_name == "Literature":
            # Count references
            return len(data.get("references", []))

        elif evidence.source_name == "ClinGen":
            # Count gene-disease validity assessments
            return data.get("validity_count", len(data.get("validities", [])))

        elif evidence.source_name == "GenCC":
            # Count gene-disease submissions
            return data.get("submission_count", len(data.get("submissions", [])))

        else:
            # Default: try to count items in common fields
            return (
                len(data.get("pmids", [])) +
                len(data.get("references", [])) +
                len(data.get("items", [])) +
                len(data.get("validities", [])) +
                len(data.get("submissions", []))
            )

    def calculate_gene_score(self, gene: Gene) -> dict[str, Any]:
        """Calculate percentile-based score for a gene

        Args:
            gene: Gene object

        Returns:
            Dictionary with score details
        """
        # Get all evidence for gene
        evidence_records = (
            self.db.query(GeneEvidence)
            .filter(GeneEvidence.gene_id == gene.id)
            .all()
        )

        if not evidence_records:
            return {
                "total_score": 0.0,
                "source_scores": {},
                "evidence_count": 0,
                "source_count": 0,
            }

        # Calculate percentile for each source
        source_percentiles = {}
        for evidence in evidence_records:
            source_name = evidence.source_name

            # Get percentiles for this source
            percentiles = self.calculate_percentiles_for_source(source_name)

            # Get this gene's percentile
            if gene.id in percentiles:
                source_percentiles[source_name] = percentiles[gene.id]
            else:
                # Shouldn't happen but handle gracefully
                source_percentiles[source_name] = 0.0

        # Sum percentiles (like R implementation)
        total_score = sum(source_percentiles.values())

        return {
            "total_score": total_score,
            "source_scores": source_percentiles,
            "evidence_count": len(evidence_records),
            "source_count": len(source_percentiles),
        }

    def update_all_scores(self) -> dict[str, Any]:
        """Recalculate all gene scores with percentile normalization

        Returns:
            Statistics about the update
        """
        from app.models.gene import GeneCuration

        stats = {
            "genes_processed": 0,
            "scores_updated": 0,
        }

        # Clear cache to force recalculation
        self._percentile_cache.clear()

        # Get all genes with evidence
        genes_with_evidence = (
            self.db.query(Gene)
            .join(GeneEvidence)
            .distinct()
            .all()
        )

        logger.info(f"Recalculating scores for {len(genes_with_evidence)} genes")

        for gene in genes_with_evidence:
            stats["genes_processed"] += 1

            # Calculate new score
            score_data = self.calculate_gene_score(gene)

            # Update curation
            curation = (
                self.db.query(GeneCuration)
                .filter(GeneCuration.gene_id == gene.id)
                .first()
            )

            if curation:
                # Store the raw percentile sum directly (0-N where N is number of sources)
                # With 2 sources, max is 2.0
                # With 5 sources, max would be 5.0
                curation.evidence_score = score_data["total_score"]

                # Store raw percentile sum in JSONB for reference
                if not curation.constraint_scores:
                    curation.constraint_scores = {}
                curation.constraint_scores["percentile_sum"] = score_data["total_score"]
                curation.constraint_scores["source_percentiles"] = score_data["source_scores"]

                self.db.add(curation)
                stats["scores_updated"] += 1

        self.db.commit()

        logger.info(f"Score update complete: {stats['scores_updated']} genes updated")
        return stats
