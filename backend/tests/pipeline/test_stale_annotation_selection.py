"""Routine runs bring stale-method and missing annotations up to date (#338, #28)."""

from datetime import datetime, timedelta

import pytest

from app.models.gene_annotation import AnnotationSource, GeneAnnotation
from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy
from app.pipeline.sources.annotations import mondo
from app.pipeline.sources.annotations.hpo import CLINICAL_GROUP_METHOD
from tests.factories import GeneFactory

# Fixtures stay independent of the current CLINICAL_GROUP_METHOD value.
STALE_METHOD = {"classification": {"clinical_group": {"method": "hpo-freq-ic-v0-test"}}}
STALE_V051 = {"classification": {"clinical_group": {"primary": "x", "scores": {}}}}  # no method
NO_GROUP = {"classification": {}}
CURRENT = {"classification": {"clinical_group": {"method": CLINICAL_GROUP_METHOD}}}


def _annotated_gene(db_session, hpo_payload: dict) -> int:
    """A gene holding one annotation per source, so only staleness can select it."""
    GeneFactory._meta.sqlalchemy_session = db_session
    gene = GeneFactory()
    payloads = {
        "hpo": hpo_payload,
        "mondo": {"provenance": {"sssom_sha256": mondo._CONFIG.get("sssom_sha256")}},
    }
    db_session.add_all(
        GeneAnnotation(gene_id=gene.id, source=name, annotations=payloads.get(name, {"x": 1}))
        for name in AnnotationPipeline(db_session).sources
    )
    db_session.flush()
    return gene.id


def _not_due(db_session, *names: str, is_active: bool = True) -> None:
    for name in names:  # other tests may leave committed rows behind: update or add
        row = db_session.query(AnnotationSource).filter_by(source_name=name).first()
        row = row or AnnotationSource(source_name=name, display_name=name)
        row.is_active = is_active
        row.next_update = datetime.utcnow() + timedelta(days=30)
        db_session.add(row)
    db_session.flush()


@pytest.mark.asyncio
async def test_incremental_selects_stale_hpo_payloads_but_not_current(db_session):
    stale = [_annotated_gene(db_session, p) for p in (STALE_METHOD, STALE_V051)]
    current = [_annotated_gene(db_session, p) for p in (CURRENT, NO_GROUP)]
    pipeline = AnnotationPipeline(db_session)

    genes = await pipeline._get_genes_to_update(
        UpdateStrategy.INCREMENTAL, None, sources=list(pipeline.sources)
    )
    ids = {g.id for g in genes}
    assert set(stale) <= ids
    assert not set(current) & ids


@pytest.mark.asyncio
async def test_stale_rows_of_a_source_that_does_not_run_add_no_genes(db_session):
    _annotated_gene(db_session, STALE_METHOD)
    pipeline = AnnotationPipeline(db_session)
    _not_due(db_session, "hpo", is_active=False)
    sources = await pipeline._get_sources_to_update(None, False)
    assert "hpo" not in sources

    genes = await pipeline._get_genes_to_update(UpdateStrategy.INCREMENTAL, None, sources=sources)
    assert genes == []


@pytest.mark.asyncio
async def test_default_run_includes_source_with_stale_annotations_even_when_not_due(db_session):
    _annotated_gene(db_session, STALE_METHOD)
    pipeline = AnnotationPipeline(db_session)
    _not_due(db_session, *pipeline.sources)

    assert await pipeline._get_sources_to_update(None, False) == ["hpo"]
    status = {s["source"]: s for s in await pipeline.check_source_status()}
    assert status["hpo"]["stale_annotation_count"] == 1
    assert status["hpo"]["update_due"] is True
    assert status["gtex"]["stale_annotation_count"] == 0  # no hook: never stale


@pytest.mark.asyncio
async def test_current_annotations_leave_not_due_sources_out(db_session):
    _annotated_gene(db_session, CURRENT)
    pipeline = AnnotationPipeline(db_session)
    _not_due(db_session, *pipeline.sources)

    assert await pipeline._get_sources_to_update(None, False) == []


@pytest.mark.asyncio
async def test_default_run_registers_and_includes_sources_without_a_row(db_session):
    pipeline = AnnotationPipeline(db_session)
    _not_due(db_session, *(s for s in pipeline.sources if s != "mondo"))

    assert await pipeline._get_sources_to_update(None, False) == ["mondo"]
    assert db_session.query(AnnotationSource).filter_by(source_name="mondo").one().is_active


@pytest.mark.asyncio
async def test_status_lists_sources_without_a_row_without_creating_it(db_session):
    pipeline = AnnotationPipeline(db_session)
    _not_due(db_session, *(s for s in pipeline.sources if s != "mondo"))

    status = {s["source"]: s for s in await pipeline.check_source_status()}
    assert status["mondo"]["is_active"] is True
    assert status["mondo"]["update_due"] is True
    assert status["mondo"]["annotation_count"] == 0
    assert status["mondo"]["stale_annotation_count"] == 0
    assert db_session.query(AnnotationSource).filter_by(source_name="mondo").first() is None
