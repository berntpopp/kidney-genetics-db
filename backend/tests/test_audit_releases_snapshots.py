"""Publishing a release keeps current genes and serves its immutable export (#288)."""

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services.release_service import ReleaseService, _load_release_genes

PREFIX = "AUDIT288_"


def _add_gene(db, symbol: str) -> None:
    db.execute(
        text("INSERT INTO genes (hgnc_id, approved_symbol, aliases) VALUES (:h, :s, '{}')"),
        {"h": f"HGNC:{symbol}", "s": symbol},
    )
    db.flush()


def _current(db) -> set[str]:
    rows = db.execute(
        text("SELECT approved_symbol FROM genes_current WHERE approved_symbol LIKE :p"),
        {"p": f"{PREFIX}%"},
    ).scalars()
    return set(rows)


async def _release_symbols(service: ReleaseService, version: str) -> set[str]:
    result = await service.get_release_genes(version, limit=1000, offset=0)
    return {
        g["approved_symbol"] for g in result["genes"] if g["approved_symbol"].startswith(PREFIX)
    }


def _sha(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_releases_keep_current_genes_and_snapshots(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.ZENODO_API_TOKEN", None)
    user_id = db_session.execute(
        text(
            "INSERT INTO users (email, username, hashed_password, role, is_active, "
            "is_verified, failed_login_attempts) "
            "VALUES ('audit288@example.org', 'audit288', 'x', 'admin', true, true, 0) "
            "RETURNING id"
        )
    ).scalar_one()
    service = ReleaseService(db_session)
    service.export_dir = tmp_path

    _add_gene(db_session, f"{PREFIX}A")
    _add_gene(db_session, f"{PREFIX}B")
    first = await service.create_release("2999.1", user_id)
    first = await service.publish_release(first.id, user_id)
    first_checksum = first.export_checksum

    # Publishing must not retire live genes.
    assert _current(db_session) == {f"{PREFIX}A", f"{PREFIX}B"}

    _add_gene(db_session, f"{PREFIX}C")
    second = await service.create_release("2999.2", user_id)
    second = await service.publish_release(second.id, user_id)

    assert _current(db_session) == {f"{PREFIX}A", f"{PREFIX}B", f"{PREFIX}C"}
    assert second.gene_count == first.gene_count + 1

    # Each release serves its own immutable snapshot.
    assert await _release_symbols(service, "2999.1") == {f"{PREFIX}A", f"{PREFIX}B"}
    assert await _release_symbols(service, "2999.2") == {
        f"{PREFIX}A",
        f"{PREFIX}B",
        f"{PREFIX}C",
    }
    assert _sha(first.export_file_path) == first_checksum
    for release in (first, second):
        export = json.loads(Path(release.export_file_path).read_text())
        assert export["gene_count"] == release.gene_count
        result = await service.get_release_genes(release.version, limit=1, offset=0)
        assert result["total"] == release.gene_count
        assert len(result["genes"]) == 1

    # A tampered snapshot is refused rather than silently served.
    Path(first.export_file_path).write_text("{}")
    _load_release_genes.cache_clear()
    with pytest.raises(ValueError, match="checksum"):
        await service.get_release_genes("2999.1", limit=10, offset=0)
