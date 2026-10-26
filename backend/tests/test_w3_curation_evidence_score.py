"""gene_curations.evidence_score mirrors gene_scores instead of a constant 0.0 (#366)."""

import pytest
from sqlalchemy import text

from app.models.gene import Gene, GeneCuration, GeneEvidence
from app.pipeline.aggregate import update_all_curations


@pytest.mark.integration
def test_curation_evidence_score_comes_from_gene_scores(db_session):
    gene = Gene(approved_symbol="KGTW3SCORE", hgnc_id="HGNC:9936606")
    db_session.add(gene)
    db_session.flush()
    db_session.add(
        GeneEvidence(
            gene_id=gene.id,
            source_name="ClinGen",
            source_detail="w3",
            evidence_data={"classifications": ["Definitive"]},
        )
    )
    db_session.flush()
    db_session.execute(text("REFRESH MATERIALIZED VIEW gene_scores"))

    expected = db_session.execute(
        text("SELECT percentage_score FROM gene_scores WHERE gene_id = :g"), {"g": gene.id}
    ).scalar_one()
    update_all_curations(db_session)

    curation = db_session.query(GeneCuration).filter_by(gene_id=gene.id).one()
    assert expected > 0
    assert curation.evidence_score == pytest.approx(float(expected))
