"""Regression for #281: retained PubTator mention samples are not a cumulative total."""

import pytest

from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


def _chunk(pmids: range) -> dict:
    mentions = [{"pmid": str(p), "score": p % 7, "title": f"t{p}"} for p in pmids]
    # Mirrors _flush_buffers output: mentions are truncated to the top 20.
    return {
        "pmids": [str(p) for p in pmids],
        "identifiers": ["6928"],
        "mentions": sorted(mentions, key=lambda m: m["score"], reverse=True)[:20],
        "total_mentions": len(mentions),
    }


@pytest.mark.unit
def test_source_detail_reports_unique_publications_not_sample_size():
    source = PubTatorUnifiedSource.__new__(PubTatorUnifiedSource)
    chunks = [_chunk(range(start, min(start + 30, 207))) for start in range(0, 207, 30)]

    data = chunks[0]
    for chunk in chunks[1:]:
        data = source._merge_evidence_data(data, chunk)
    data = source._merge_evidence_data(data, chunks[3])  # replayed chunk

    assert data["publication_count"] == 207
    assert len(data["mentions"]) == 20  # retained display sample only
    assert source._get_source_detail(data) == "PubTator: 207 publications"
