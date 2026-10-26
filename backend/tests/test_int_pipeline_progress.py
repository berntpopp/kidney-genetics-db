"""#370: one honest progress line for parallel sources, and lean status payloads."""

from unittest.mock import MagicMock

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
