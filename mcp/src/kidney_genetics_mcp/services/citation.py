"""Citation assembly with date-confidence gating."""

from __future__ import annotations

from typing import Any

#: Software concept DOI for the Kidney-Genetics-DB code archive (always resolves
#: to the latest release). Cited alongside the per-release dataset DOI.
CONCEPT_DOI = "10.5281/zenodo.19316248"


def build_citation(pub: dict[str, Any]) -> dict[str, Any]:
    """Return ``recommended_citation`` and ``date_confidence`` for a publication.

    Applies date-confidence gating: when the publication's ``year`` is missing
    the citation is marked ``unverified``, the year is omitted from the string,
    and a ``" (publication date unverified)"`` suffix is appended so a consuming
    model never silently presents an unverified date as authoritative.

    Args:
        pub: A publication-like dict with optional ``authors``, ``title``,
            ``journal``, ``year``, ``pmid``, ``doi`` keys.

    Returns:
        ``{"recommended_citation": str, "date_confidence": "verified" |
        "unverified"}``.
    """
    year = pub.get("year")
    confidence = "verified" if year else "unverified"
    parts: list[str] = []
    authors = str(pub.get("authors") or "").strip().rstrip(".")
    if authors:
        parts.append(authors)
    if pub.get("title"):
        parts.append(str(pub["title"]).strip().rstrip("."))
    if pub.get("journal"):
        parts.append(str(pub["journal"]).strip())
    if year:
        parts.append(str(year))
    pmid = str(pub.get("pmid") or "").replace("PMID:", "").strip()
    if pmid:
        parts.append(f"PMID:{pmid}")
    if pub.get("doi"):
        parts.append(f"doi:{pub['doi']}")
    citation = ". ".join(p for p in parts if p)
    if confidence == "unverified":
        citation += " (publication date unverified)"
    return {"recommended_citation": citation, "date_confidence": confidence}


def build_release_citation(release: dict[str, Any]) -> dict[str, Any]:
    """Build the dataset citation for a published data release.

    Prefers the backend-supplied ``citation_text`` verbatim when present;
    otherwise assembles one from the release ``version`` and dataset ``doi``.
    The software concept DOI (:data:`CONCEPT_DOI`) is always included so a
    consuming model can cite both the dataset snapshot and the software archive.

    Args:
        release: A release-like dict with optional ``version``, ``doi``,
            ``citation_text`` keys.

    Returns:
        ``{"recommended_citation": str, "version": str | None, "doi": str |
        None, "concept_doi": str}``.
    """
    version = release.get("version")
    doi = release.get("doi")
    citation_text = release.get("citation_text")
    if citation_text:
        citation = str(citation_text).strip()
    else:
        parts = ["Kidney-Genetics-DB"]
        if version:
            parts.append(f"data release {version}")
        if doi:
            parts.append(f"doi:{doi}")
        citation = ". ".join(parts)
    citation = f"{citation} Software concept DOI: {CONCEPT_DOI}."
    return {
        "recommended_citation": citation,
        "version": version,
        "doi": doi,
        "concept_doi": CONCEPT_DOI,
    }
