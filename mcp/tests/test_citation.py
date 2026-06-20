"""Tests for citation assembly + date-confidence gating."""

from __future__ import annotations

from kidney_genetics_mcp.services.citation import (
    CONCEPT_DOI,
    build_citation,
    build_release_citation,
)


def test_citation_verified() -> None:
    out = build_citation(
        {
            "authors": "Doe J, Roe A.",
            "title": "A kidney gene study.",
            "journal": "Nephrol",
            "year": 2021,
            "pmid": "PMID:12345",
            "doi": "10.1/x",
        }
    )
    assert out["date_confidence"] == "verified"
    cite = out["recommended_citation"]
    assert "2021" in cite
    assert "PMID:12345" in cite
    assert "doi:10.1/x" in cite
    assert "unverified" not in cite


def test_citation_unverified_gating() -> None:
    out = build_citation({"authors": "Doe J", "title": "X", "journal": "J"})
    assert out["date_confidence"] == "unverified"
    cite = out["recommended_citation"]
    assert cite.endswith("(publication date unverified)")
    # year is omitted entirely
    assert "None" not in cite


def test_release_citation_uses_citation_text() -> None:
    out = build_release_citation(
        {"version": "2026.06", "doi": "10.5281/zenodo.999", "citation_text": "Cite me."}
    )
    assert out["version"] == "2026.06"
    assert out["doi"] == "10.5281/zenodo.999"
    assert out["concept_doi"] == CONCEPT_DOI
    assert out["recommended_citation"].startswith("Cite me.")
    assert CONCEPT_DOI in out["recommended_citation"]


def test_release_citation_assembled() -> None:
    out = build_release_citation({"version": "2026.06", "doi": "10.5281/zenodo.999"})
    cite = out["recommended_citation"]
    assert "2026.06" in cite
    assert "doi:10.5281/zenodo.999" in cite
    assert CONCEPT_DOI in cite
