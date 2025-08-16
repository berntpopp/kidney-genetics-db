"""
Evidence aggregation and scoring module

Combines evidence from multiple sources and calculates confidence scores
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.gene import Gene, GeneCuration, GeneEvidence

logger = logging.getLogger(__name__)


class EvidenceAggregator:
    """Aggregates evidence from multiple sources and calculates scores"""

    def __init__(self, db: Session):
        """Initialize aggregator with database session"""
        self.db = db
        # Evidence source weights (configurable)
        self.source_weights = {
            "PanelApp": 1.0,  # High confidence - expert curated (combines UK and AU)
            "HPO": 0.8,  # Good - phenotype associations
            "PubTator": 0.6,  # Moderate - literature mining
            "Literature": 1.0,  # High - manual curation
        }

        # Evidence type scoring factors
        self.scoring_factors = {
            "panel_count": 5,  # Points per panel
            "phenotype_count": 2,  # Points per HPO term
            "publication_count": 1,  # Points per publication
            "disease_count": 3,  # Points per disease association
        }

    def calculate_gene_score(self, gene: Gene) -> float:
        """Calculate evidence score for a gene

        Args:
            gene: Gene object with evidence

        Returns:
            Evidence score (0-100)
        """
        total_score = 0.0
        max_possible = 0.0

        # Get all evidence for gene
        evidence_records = self.db.query(GeneEvidence).filter(GeneEvidence.gene_id == gene.id).all()

        for evidence in evidence_records:
            source_weight = self.source_weights.get(evidence.source_name, 0.5)
            evidence_data = evidence.evidence_data or {}

            # Score based on evidence type
            if evidence.source_name == "PanelApp":
                # Score based on number of panels
                panel_count = len(evidence_data.get("panels", []))
                score = panel_count * self.scoring_factors["panel_count"]
                total_score += score * source_weight
                max_possible += 50 * source_weight  # Max 10 panels expected

            elif evidence.source_name == "HPO":
                # Score based on phenotype associations
                phenotype_count = len(evidence_data.get("phenotypes", []))
                disease_count = len(evidence_data.get("disease_associations", []))
                score = (
                    phenotype_count * self.scoring_factors["phenotype_count"]
                    + disease_count * self.scoring_factors["disease_count"]
                )
                total_score += min(score, 30) * source_weight  # Cap at 30
                max_possible += 30 * source_weight

            elif evidence.source_name == "PubTator":
                # Score based on publication count
                pub_count = evidence_data.get("publication_count", 0)
                score = min(pub_count * self.scoring_factors["publication_count"], 20)
                total_score += score * source_weight
                max_possible += 20 * source_weight

        # Normalize to 0-100 scale
        if max_possible > 0:
            normalized_score = (total_score / max_possible) * 100
            return min(100.0, normalized_score)

        return 0.0

    def classify_gene(self, score: float) -> str:
        """Classify gene based on evidence score

        Args:
            score: Evidence score (0-100)

        Returns:
            Classification category
        """
        if score >= 80:
            return "Definitive"
        elif score >= 60:
            return "Strong"
        elif score >= 40:
            return "Moderate"
        elif score >= 20:
            return "Limited"
        else:
            return "Insufficient"

    def aggregate_gene_evidence(self, gene: Gene) -> dict[str, Any]:
        """Aggregate all evidence for a gene

        Args:
            gene: Gene object

        Returns:
            Aggregated evidence summary
        """
        evidence_records = self.db.query(GeneEvidence).filter(GeneEvidence.gene_id == gene.id).all()

        # Collect evidence by type
        panelapp_panels = []
        hpo_terms = []
        pubtator_pmids = []
        literature_refs = []
        diagnostic_panels = []

        for evidence in evidence_records:
            data = evidence.evidence_data or {}

            if evidence.source_name == "PanelApp":
                for panel in data.get("panels", []):
                    panel_str = f"{panel.get('name')} ({panel.get('source', 'UK')})"
                    if panel_str not in panelapp_panels:
                        panelapp_panels.append(panel_str)

            elif evidence.source_name == "HPO":
                for phenotype in data.get("phenotypes", []):
                    # Handle both string and dict formats
                    if isinstance(phenotype, str):
                        hpo_term = phenotype
                    else:
                        hpo_term = f"{phenotype.get('hpo_id')}: {phenotype.get('name')}"
                    if hpo_term not in hpo_terms:
                        hpo_terms.append(hpo_term)

            elif evidence.source_name == "PubTator":
                pmids = data.get("pmids", [])
                pubtator_pmids.extend(
                    [str(pmid) for pmid in pmids if str(pmid) not in pubtator_pmids]
                )

        return {
            "evidence_count": len(evidence_records),
            "source_count": len({e.source_name for e in evidence_records}),
            "panelapp_panels": panelapp_panels[:50],  # Limit arrays
            "hpo_terms": hpo_terms[:50],
            "pubtator_pmids": pubtator_pmids[:100],
            "literature_refs": literature_refs[:50],
            "diagnostic_panels": diagnostic_panels[:20],
        }

    def update_gene_curation(self, gene: Gene) -> GeneCuration:
        """Update or create curation record for a gene

        Args:
            gene: Gene object

        Returns:
            Updated GeneCuration object
        """
        # Get or create curation record
        curation = self.db.query(GeneCuration).filter(GeneCuration.gene_id == gene.id).first()

        if not curation:
            curation = GeneCuration(gene_id=gene.id)
            self.db.add(curation)

        # Aggregate evidence
        aggregated = self.aggregate_gene_evidence(gene)

        # Update curation fields
        curation.evidence_count = aggregated["evidence_count"]
        curation.source_count = aggregated["source_count"]
        curation.panelapp_panels = aggregated["panelapp_panels"]
        curation.hpo_terms = aggregated["hpo_terms"]
        curation.pubtator_pmids = aggregated["pubtator_pmids"]
        curation.literature_refs = aggregated["literature_refs"]
        curation.diagnostic_panels = aggregated["diagnostic_panels"]

        # Calculate and set score
        score = self.calculate_gene_score(gene)
        curation.evidence_score = score
        curation.classification = self.classify_gene(score)

        self.db.commit()
        return curation


def update_all_curations(db: Session) -> dict[str, Any]:
    """Update curation records for all genes with evidence

    Args:
        db: Database session

    Returns:
        Statistics about the update
    """
    stats = {
        "genes_processed": 0,
        "curations_created": 0,
        "curations_updated": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    aggregator = EvidenceAggregator(db)

    # Get all genes with evidence
    genes_with_evidence = db.query(Gene).join(GeneEvidence).distinct().all()

    logger.info(f"Updating curations for {len(genes_with_evidence)} genes")

    for gene in genes_with_evidence:
        stats["genes_processed"] += 1

        # Check if curation exists
        existing = db.query(GeneCuration).filter(GeneCuration.gene_id == gene.id).first()

        # Update curation
        curation = aggregator.update_gene_curation(gene)

        if existing:
            stats["curations_updated"] += 1
        else:
            stats["curations_created"] += 1

        logger.debug(
            f"Updated curation for {gene.approved_symbol}: "
            f"score={curation.evidence_score:.1f}, "
            f"classification={curation.classification}"
        )

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    stats["duration"] = (
        datetime.fromisoformat(stats["completed_at"]) - datetime.fromisoformat(stats["started_at"])
    ).total_seconds()

    logger.info(
        f"Curation update complete: {stats['genes_processed']} genes, "
        f"{stats['curations_created']} created, {stats['curations_updated']} updated"
    )

    return stats
