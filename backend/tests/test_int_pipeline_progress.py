"""#370: one honest progress line for parallel sources, and lean status payloads."""

import time
from unittest.mock import MagicMock

import pytest

from app.models.progress import DataSourceProgress, _public_metadata
from app.pipeline.annotation_pipeline import AnnotationPipeline


def test_parallel_sources_share_one_progress_line():
    pipeline = AnnotationPipeline(MagicMock())
    pipeline.progress_tracker = MagicMock()
    pipeline._sources_total = 3

    pipeline._report("hpo", "fetching")
    pipeline._report("ensembl", "writing 5151")
    last = pipeline.progress_tracker.update.call_args.kwargs
    assert last["operation"] == "0/3 sources done · hpo: fetching, ensembl: writing 5151"
    assert (last["current_item"], last["total_items"], last["force"]) == (0, 3, False)

    pipeline._report("ensembl", None)  # a finished source is a forced milestone
    last = pipeline.progress_tracker.update.call_args.kwargs
    assert last["operation"] == "1/3 sources done · hpo: fetching"
    assert (last["current_item"], last["force"]) == (1, True)


def test_status_payload_counts_checkpoint_genes_instead_of_listing_them():
    assert _public_metadata({"gene_ids": list(range(5184)), "strategy": "full"}) == {
        "gene_count": 5184,
        "strategy": "full",
    }
    row = DataSourceProgress(source_name="annotation_pipeline", progress_metadata=None)
    assert row.to_dict()["metadata"] == {}


def _eta_pipeline(expected: dict, started_ago: dict, finished=()) -> AnnotationPipeline:
    pipeline = AnnotationPipeline(MagicMock())
    pipeline._todo = list(expected)
    pipeline._expected = dict(expected)
    pipeline._finished = set(finished)
    now = time.monotonic()
    pipeline._started = {name: now - ago for name, ago in started_ago.items()}
    return pipeline


def test_seconds_left_from_last_durations():
    # hgnc/mondo run alone; gtex, hpo, descartes share the 3-wide parallel phase
    p = _eta_pipeline(
        {"hgnc": 10, "gtex": 60, "hpo": 300, "descartes": 30, "mondo": 20},
        started_ago={"hgnc": 10, "gtex": 20, "hpo": 100, "descartes": 30},
        finished={"hgnc"},
    )
    # parallel left: gtex 40, hpo 200, descartes 0 -> max(200, 240/3)=200; + mondo 20
    assert p._seconds_left() == pytest.approx(220, abs=1)


def test_no_estimate_without_history_and_overdue_counts_as_zero():
    assert _eta_pipeline({"hpo": None, "gtex": 60}, {})._seconds_left() is None
    overdue = _eta_pipeline({"hpo": 60}, started_ago={"hpo": 600})
    assert overdue._seconds_left() == 0  # the page then says it runs longer than last time
