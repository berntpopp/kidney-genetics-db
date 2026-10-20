"""Publishing a release keeps current genes and serves its immutable export (#288)."""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services import release_service as rs
from app.services.release_service import ReleaseService

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


def _forbid_export_reads(monkeypatch) -> None:
    def boom(*_args, **_kwargs):
        raise AssertionError("full export must not be read on the request path")

    monkeypatch.setattr(rs, "_iter_export_genes", boom)
    monkeypatch.setattr(ReleaseService, "_calculate_checksum", staticmethod(boom))


@pytest.fixture
def service(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.ZENODO_API_TOKEN", None)
    rs._read_sidecar.cache_clear()
    rs._failed_snapshots.clear()
    svc = ReleaseService(db_session)
    svc.export_dir = tmp_path
    return svc


@pytest.fixture
def user_id(db_session) -> int:
    return db_session.execute(
        text(
            "INSERT INTO users (email, username, hashed_password, role, is_active, "
            "is_verified, failed_login_attempts) "
            "VALUES ('audit288@example.org', 'audit288', 'x', 'admin', true, true, 0) "
            "RETURNING id"
        )
    ).scalar_one()


async def _publish(service, user_id, version):
    release = await service.create_release(version, user_id)
    return await service.publish_release(release.id, user_id)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_releases_keep_current_genes_and_snapshots(
    db_session, service, user_id, monkeypatch
):
    _add_gene(db_session, f"{PREFIX}A")
    _add_gene(db_session, f"{PREFIX}B")
    first = await _publish(service, user_id, "2999.1")
    first_checksum = first.export_checksum

    # Publishing must not retire live genes.
    assert _current(db_session) == {f"{PREFIX}A", f"{PREFIX}B"}

    _add_gene(db_session, f"{PREFIX}C")
    second = await _publish(service, user_id, "2999.2")

    assert _current(db_session) == {f"{PREFIX}A", f"{PREFIX}B", f"{PREFIX}C"}
    assert second.gene_count == first.gene_count + 1

    # Pages come from the small sidecar; the full export is never read here.
    _forbid_export_reads(monkeypatch)
    assert await _release_symbols(service, "2999.1") == {f"{PREFIX}A", f"{PREFIX}B"}
    assert await _release_symbols(service, "2999.2") == {
        f"{PREFIX}A",
        f"{PREFIX}B",
        f"{PREFIX}C",
    }
    assert _sha(first.export_file_path) == first_checksum
    for release in (first, second):
        assert rs._sidecar_path(release.export_file_path).exists()
        export = json.loads(Path(release.export_file_path).read_text())
        assert export["gene_count"] == release.gene_count == len(export["genes"])
        result = await service.get_release_genes(release.version, limit=1, offset=0)
        assert result["total"] == release.gene_count
        assert len(result["genes"]) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gene_count_and_zenodo_use_exported_rows(db_session, service, user_id, monkeypatch):
    seen = {}

    class FakeZenodo:
        async def mint_doi_for_release(self, **kwargs):
            seen["gene_count"] = kwargs["gene_count"]
            # A gene added after the export must not change the release count.
            _add_gene(db_session, f"{PREFIX}LATE")
            return {"doi": "10.5281/zenodo.0"}

        async def close(self):
            pass

    monkeypatch.setattr(service, "_get_zenodo_service", lambda: FakeZenodo())
    _add_gene(db_session, f"{PREFIX}A")
    release = await _publish(service, user_id, "2999.3")
    exported = json.loads(Path(release.export_file_path).read_text())["gene_count"]
    assert release.gene_count == exported == seen["gene_count"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_legacy_release_builds_sidecar_once(db_session, service, user_id, monkeypatch):
    _add_gene(db_session, f"{PREFIX}A")
    release = await _publish(service, user_id, "2999.4")
    sidecar = rs._sidecar_path(release.export_file_path)
    sidecar.unlink()  # simulate a release published before sidecars existed
    rs._read_sidecar.cache_clear()

    calls = []
    real_iter = rs._iter_export_genes
    monkeypatch.setattr(rs, "_iter_export_genes", lambda p: calls.append(p) or real_iter(p))

    results = await asyncio.gather(
        *(service.get_release_genes("2999.4", limit=1000, offset=0) for _ in range(4))
    )
    assert len(calls) == 1
    assert all(f"{PREFIX}A" in {g["approved_symbol"] for g in r["genes"]} for r in results)
    assert sidecar.exists()
    assert _sha(release.export_file_path) == release.export_checksum


@pytest.mark.integration
@pytest.mark.asyncio
async def test_corrupt_snapshot_is_generic_500_and_not_rehashed(
    async_client, db_session, service, user_id, monkeypatch
):
    _add_gene(db_session, f"{PREFIX}A")
    release = await _publish(service, user_id, "2999.5")
    rs._sidecar_path(release.export_file_path).unlink()
    Path(release.export_file_path).write_text("{}")

    hashes = []
    real_hash = ReleaseService._calculate_checksum
    monkeypatch.setattr(
        ReleaseService,
        "_calculate_checksum",
        staticmethod(lambda p: hashes.append(p) or real_hash(p)),
    )
    for _ in range(2):
        response = await async_client.get("/api/releases/2999.5/genes")
        assert response.status_code == 500
        assert str(service.export_dir) not in response.text
        assert "Release snapshot unavailable" in response.text
    assert len(hashes) == 1


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["", "{not json", "{}"])
async def test_unreadable_sidecar_is_generic_500(
    async_client, db_session, service, user_id, content
):
    _add_gene(db_session, f"{PREFIX}A")
    release = await _publish(service, user_id, "2999.6")
    rs._sidecar_path(release.export_file_path).write_text(content)
    rs._read_sidecar.cache_clear()

    response = await async_client.get("/api/releases/2999.6/genes")
    assert response.status_code == 500
    assert str(service.export_dir) not in response.text
    assert "Release snapshot unavailable" in response.text
    assert not list(service.export_dir.glob("*.tmp"))
