"""Tests for AnnotationPipeline._bulk_upsert_annotations."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation


@pytest.mark.unit
class TestBulkUpsertAnnotations:
    """Test the bulk upsert path in the annotation pipeline."""

    def _make_pipeline(self, db_session: Session):
        """Create a minimal AnnotationPipeline for testing."""
        from app.pipeline.annotation_pipeline import AnnotationPipeline

        return AnnotationPipeline(db_session)

    def test_bulk_upsert_inserts_new_annotations(self, db_session: Session):
        """New gene annotations are inserted via bulk upsert."""
        gene = db_session.query(Gene).first()
        if not gene:
            pytest.skip("No genes in database")

        db_session.execute(
            text(
                "DELETE FROM gene_annotations "
                "WHERE gene_id = :gid AND source = :src AND version = :ver"
            ),
            {"gid": gene.id, "src": "_test_bulk", "ver": "1.0"},
        )
        db_session.commit()

        pipeline = self._make_pipeline(db_session)
        batch_data = {gene.id: {"test_field": "test_value", "score": 0.95}}

        count = pipeline._bulk_upsert_annotations("_test_bulk", "1.0", batch_data)

        assert count == 1
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk", version="1.0")
            .first()
        )
        assert ann is not None
        assert ann.annotations["test_field"] == "test_value"
        assert ann.annotations["score"] == 0.95

        db_session.delete(ann)
        db_session.commit()

    def test_bulk_upsert_updates_existing_annotations(self, db_session: Session):
        """Existing annotations are updated (not duplicated) by bulk upsert."""
        gene = db_session.query(Gene).first()
        if not gene:
            pytest.skip("No genes in database")

        pipeline = self._make_pipeline(db_session)
        pipeline._bulk_upsert_annotations("_test_bulk", "1.0", {gene.id: {"value": "old"}})

        count = pipeline._bulk_upsert_annotations(
            "_test_bulk", "1.0", {gene.id: {"value": "new", "extra": 42}}
        )

        assert count == 1
        ann = (
            db_session.query(GeneAnnotation)
            .filter_by(gene_id=gene.id, source="_test_bulk", version="1.0")
            .first()
        )
        assert ann is not None
        assert ann.annotations["value"] == "new"
        assert ann.annotations["extra"] == 42

        db_session.delete(ann)
        db_session.commit()

    def test_bulk_upsert_handles_multiple_genes(self, db_session: Session):
        """Multiple genes are upserted in a single call."""
        genes = db_session.query(Gene).limit(5).all()
        if len(genes) < 2:
            pytest.skip("Need at least 2 genes")

        pipeline = self._make_pipeline(db_session)
        batch_data = {g.id: {"symbol": g.approved_symbol} for g in genes}

        count = pipeline._bulk_upsert_annotations("_test_bulk", "1.0", batch_data)
        assert count == len(genes)

        for g in genes:
            ann = (
                db_session.query(GeneAnnotation)
                .filter_by(gene_id=g.id, source="_test_bulk", version="1.0")
                .first()
            )
            assert ann is not None
            assert ann.annotations["symbol"] == g.approved_symbol

        db_session.execute(
            text("DELETE FROM gene_annotations WHERE source = '_test_bulk'")
        )
        db_session.commit()

    def test_bulk_upsert_empty_dict_returns_zero(self, db_session: Session):
        """Empty batch_data returns 0 without DB interaction."""
        pipeline = self._make_pipeline(db_session)
        count = pipeline._bulk_upsert_annotations("_test_bulk", "1.0", {})
        assert count == 0

    def test_bulk_upsert_handles_large_batch(self, db_session: Session):
        """Batches exceeding chunk_size (500) are split correctly."""
        genes = db_session.query(Gene).limit(600).all()
        if len(genes) < 600:
            pytest.skip("Need at least 600 genes for large batch test")

        pipeline = self._make_pipeline(db_session)
        batch_data = {g.id: {"idx": i} for i, g in enumerate(genes)}

        count = pipeline._bulk_upsert_annotations("_test_bulk", "1.0", batch_data)
        assert count == len(genes)

        db_session.execute(
            text("DELETE FROM gene_annotations WHERE source = '_test_bulk'")
        )
        db_session.commit()
