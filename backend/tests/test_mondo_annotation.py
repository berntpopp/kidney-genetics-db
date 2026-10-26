"""MONDO disease mapping via the pinned SSSOM, skos:exactMatch only (#28).

The fixture excerpt holds real rows of the pinned mondo.sssom.tsv (v2026-10-06). The
pinned file has no ambiguous exactMatch, so the ambiguity test uses a synthetic file
with placeholder IDs.
"""

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.models.gene import GeneEvidence
from app.models.gene_annotation import GeneAnnotation
from app.pipeline.sources.annotations import mondo
from app.pipeline.sources.annotations.mondo import (
    MondoAnnotationSource,
    map_disease_ids,
    parse_sssom,
)
from tests.factories import GeneFactory

EXCERPT = Path(__file__).parent / "fixtures" / "mondo" / "mondo_sssom_excerpt.tsv"
PROV = {"mondo_release": "test"}


def _map(inputs: dict[str, set[str]], path: Path = EXCERPT) -> dict:
    mappings, labels = parse_sssom(path)
    return map_disease_ids(inputs, mappings, labels, PROV)


def test_exact_match_maps_with_label_and_orpha_prefix_normalised():
    result = _map({"OMIM:173900": {"HPO", "GenCC"}, "ORPHA:730": {"HPO"}})
    assert result["mondo_diseases"] == [
        {
            "mondo_id": "MONDO:0004691",
            "label": "autosomal dominant polycystic kidney disease",
            "source_ids": ["ORPHA:730"],
            "sources": ["HPO"],
        },
        {
            "mondo_id": "MONDO:0008263",
            "label": "polycystic kidney disease 1",
            "source_ids": ["OMIM:173900"],
            "sources": ["GenCC", "HPO"],
        },
    ]
    assert result["unmapped"] == [] and result["ambiguous"] == []


def test_ambiguous_exact_match_is_not_mapped_and_reported(tmp_path):
    synthetic = tmp_path / "ambiguous.sssom.tsv"
    synthetic.write_text(
        "subject_id\tsubject_label\tpredicate_id\tobject_id\n"
        "MONDO:9999991\ta\tskos:exactMatch\tOMIM:999991\n"
        "MONDO:9999992\tb\tskos:exactMatch\tOMIM:999991\n"
    )
    result = _map({"OMIM:999991": {"HPO"}}, synthetic)
    assert result["mondo_diseases"] == []
    assert result["ambiguous"] == [
        {
            "source_id": "OMIM:999991",
            "sources": ["HPO"],
            "candidates": ["MONDO:9999991", "MONDO:9999992"],
            "reason": "multiple exactMatch",
        }
    ]
    assert result["ambiguous_count"] == 1


def test_no_match_and_non_exact_predicate_are_unmapped():
    # ICD10CM:I00-I99 has only a skos:broadMatch row in the file
    result = _map({"OMIM:999999": {"GenCC"}, "ICD10CM:I00-I99": {"GenCC"}})
    assert result["mondo_diseases"] == []
    assert [(u["source_id"], u["reason"]) for u in result["unmapped"]] == [
        ("ICD10CM:I00-I99", "no exactMatch"),
        ("OMIM:999999", "no exactMatch"),
    ]


def test_mondo_ids_pass_through_after_format_check():
    result = _map({"MONDO:0008263": {"ClinGen"}, "MONDO:123": {"ClinGen"}, "junk": {"GenCC"}})
    assert [d["mondo_id"] for d in result["mondo_diseases"]] == ["MONDO:0008263"]
    assert result["mondo_diseases"][0]["label"] == "polycystic kidney disease 1"
    assert {u["source_id"]: u["reason"] for u in result["unmapped"]} == {
        "MONDO:123": "invalid MONDO ID",
        "junk": "invalid identifier",
    }


def test_registered_with_seven_day_cache_and_pinned_release():
    from app.pipeline.annotation_pipeline import AnnotationPipeline

    assert AnnotationPipeline(MagicMock()).sources["mondo"] is MondoAnnotationSource
    source = MondoAnnotationSource(MagicMock())
    assert source.cache_ttl_days == 7
    assert source.version == "2026-10-06"
    assert "/mondo/9bfccbe9217cdfa6a225058bfa6e4bd55512b432/" in source.bulk_file_url
    assert source.provenance()["predicate"] == "skos:exactMatch"


# ---------- fail closed ----------


def _gene() -> MagicMock:
    return MagicMock(id=1, approved_symbol="PKD1", hgnc_id="HGNC:9008")


def _source(tmp_path: Path) -> MondoAnnotationSource:
    source = MondoAnnotationSource(MagicMock())
    source.bulk_cache_dir = tmp_path
    source._disease_ids = MagicMock(return_value={1: {"OMIM:173900": {"HPO"}}})
    return source


@pytest.mark.asyncio
async def test_sha256_mismatch_fails_and_deletes_cached_file(tmp_path):
    source = _source(tmp_path)
    cached = source._bulk_cache_path()
    cached.write_text(EXCERPT.read_text())  # fresh cache, wrong content
    with pytest.raises(ValueError, match="sha256"):
        await source.fetch_batch([_gene()])
    assert not cached.exists()
    with pytest.raises(ValueError, match="sha256"):  # the run stays failed
        await source.fetch_annotation(_gene())


@pytest.mark.asyncio
async def test_unreachable_url_with_no_cached_file_fails(tmp_path):
    source = _source(tmp_path)
    source.bulk_file_url = "http://127.0.0.1:9/mondo.sssom.tsv"
    with pytest.raises(httpx.ConnectError):
        await source.fetch_batch([_gene()])
    source.store_annotation = MagicMock()
    cache = MagicMock(get=AsyncMock(return_value=None), set=AsyncMock())
    with patch("app.pipeline.sources.annotations.base.get_cache_service", return_value=cache):
        assert await source.update_gene(_gene()) is False
    source.store_annotation.assert_not_called()


@pytest.mark.asyncio
async def test_missing_pin_fails(tmp_path):
    source = _source(tmp_path)
    with patch.dict(mondo._CONFIG, {"sssom_sha256": ""}):
        with pytest.raises(ValueError, match="not configured"):
            await source.fetch_batch([_gene()])


@pytest.mark.asyncio
async def test_verified_file_maps_and_cached_payload_from_other_pin_is_rejected(tmp_path):
    source = _source(tmp_path)
    cached = source._bulk_cache_path()
    cached.write_text(EXCERPT.read_text())
    sha = hashlib.sha256(cached.read_bytes()).hexdigest()
    with patch.dict(mondo._CONFIG, {"sssom_sha256": sha}):
        result = (await source.fetch_batch([_gene()]))[1]
        assert result["mondo_diseases"][0]["mondo_id"] == "MONDO:0008263"
        assert source._is_valid_annotation(result)
    assert not source._is_valid_annotation(result)  # pin changed: cached payload is stale


# ---------- inputs from stored HPO annotations and evidence, provenance stored ----------


def test_reads_hpo_gencc_clingen_ids_and_stores_provenance(db_session):
    GeneFactory._meta.sqlalchemy_session = db_session
    gene = GeneFactory()
    db_session.add_all(
        [
            GeneAnnotation(
                gene_id=gene.id,
                source="hpo",
                annotations={"diseases": [{"id": "OMIM:173900"}, {"id": "ORPHA:730"}]},
            ),
            GeneEvidence(
                gene_id=gene.id,
                source_name="GenCC",
                source_detail="t",
                evidence_data={
                    "submissions": [
                        {
                            "raw_data": {
                                "disease_curie": "MONDO:0008263",
                                "disease_original_curie": "OMIM:173900",
                            }
                        }
                    ]
                },
            ),
            GeneEvidence(
                gene_id=gene.id,
                source_name="ClinGen",
                source_detail="t",
                evidence_data={"validities": [{"mondo_id": "MONDO:0013131"}]},
            ),
        ]
    )
    db_session.flush()

    source = MondoAnnotationSource(db_session)
    source._mappings, source._labels = parse_sssom(EXCERPT)
    inputs = source._disease_ids([gene.id])[gene.id]
    assert inputs == {
        "OMIM:173900": {"HPO", "GenCC"},
        "ORPHA:730": {"HPO"},
        "MONDO:0008263": {"GenCC"},
        "MONDO:0013131": {"ClinGen"},
    }

    payload = map_disease_ids(inputs, source._mappings, source._labels, source.provenance())
    source.batch_mode = True
    source.store_annotation(gene, payload)
    db_session.flush()
    stored = db_session.query(GeneAnnotation).filter_by(gene_id=gene.id, source="mondo").one()
    assert stored.version == "2026-10-06"
    assert stored.annotations["provenance"] == {
        "mondo_release": "2026-10-06",
        "sssom_url": source.bulk_file_url,
        "sssom_sha256": "ec15afdb32fab3d3cb679d357e25ef4fb38b5e2c468ff4ac5456da10e2f6c80b",
        "predicate": "skos:exactMatch",
        "license": "CC BY 4.0",
    }
    by_id = {d["mondo_id"]: d for d in stored.annotations["mondo_diseases"]}
    assert by_id["MONDO:0008263"]["source_ids"] == ["MONDO:0008263", "OMIM:173900"]
    assert by_id["MONDO:0008263"]["sources"] == ["GenCC", "HPO"]
    assert by_id["MONDO:0013131"]["sources"] == ["ClinGen"]


def test_obsolete_mondo_targets_are_unmapped_not_shown():
    # Real pinned row: OMIM:613740 -> MONDO:0000911 "obsolete dilated cardiomyopathy 1T"
    result = _map(
        {"OMIM:613740": {"HPO"}, "MONDO:0000911": {"ClinGen"}, "MONDO:0013212": {"ClinGen"}}
    )
    assert {u["source_id"]: u["reason"] for u in result["unmapped"]} == {
        "OMIM:613740": "obsolete MONDO term",
        "MONDO:0000911": "obsolete MONDO term",
    }
    # A direct MONDO ID absent from the SSSOM passes through without an invented label
    assert result["mondo_diseases"] == [
        {
            "mondo_id": "MONDO:0013212",
            "label": None,
            "source_ids": ["MONDO:0013212"],
            "sources": ["ClinGen"],
        }
    ]


@pytest.mark.asyncio
async def test_pipeline_runs_mondo_after_the_parallel_phase(db_session):
    from app.pipeline.annotation_pipeline import AnnotationPipeline, UpdateStrategy

    pipeline = AnnotationPipeline(db_session)
    calls: list = []

    async def parallel(sources, gene_ids, force):
        calls.append(sorted(sources))
        return {s: {} for s in sources}

    async def single(source_name, gene_ids, force, db):
        calls.append(source_name)
        return {}

    with (
        patch.object(
            pipeline, "_get_sources_to_update", AsyncMock(return_value=["mondo", "hpo", "gtex"])
        ),
        patch.object(pipeline, "_get_genes_to_update", AsyncMock(return_value=[MagicMock(id=1)])),
        patch.object(pipeline, "_update_source_with_session", side_effect=single),
        patch.object(pipeline, "_update_sources_parallel", side_effect=parallel),
        patch.object(pipeline, "_save_checkpoint", AsyncMock()) as checkpoint,
        patch.object(pipeline, "_refresh_materialized_view", AsyncMock(return_value=True)),
        patch("app.pipeline.annotation_pipeline.SessionLocal", MagicMock()),
        patch("app.core.progress_tracker.ProgressTracker._commit_and_broadcast"),
    ):
        await pipeline.run_update(strategy=UpdateStrategy.FULL)
    assert calls == [["gtex", "hpo"], "mondo"]
    assert "mondo" in checkpoint.await_args.args[0]["sources_remaining"]


def test_single_gene_update_endpoint_knows_mondo():
    from app.api.endpoints.annotation_updates import SOURCE_CLASSES

    assert SOURCE_CLASSES["mondo"] is MondoAnnotationSource
