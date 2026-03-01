"""
Tests for the BulkDataSourceMixin class.

Verifies bulk file download, caching, parsing, and gene lookup
functionality provided by the mixin.
"""

from pathlib import Path

import pytest


@pytest.mark.unit
class TestMixinAttributesExist:
    """BulkDataSourceMixin exposes expected class attributes."""

    def test_mixin_attributes_exist(self) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()

        assert hasattr(mixin, "bulk_file_url")
        assert hasattr(mixin, "bulk_cache_dir")
        assert hasattr(mixin, "bulk_cache_ttl_hours")
        assert hasattr(mixin, "bulk_file_format")

        # Verify default values
        assert mixin.bulk_file_url == ""
        assert mixin.bulk_cache_dir == Path("data/bulk_cache")
        assert mixin.bulk_cache_ttl_hours == 168  # 7 days
        assert mixin.bulk_file_format == "tsv"


@pytest.mark.unit
class TestParseBulkFileIsAbstract:
    """parse_bulk_file raises NotImplementedError by default."""

    def test_parse_bulk_file_is_abstract(self, tmp_path: Path) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        dummy_path = tmp_path / "dummy.tsv"
        dummy_path.write_text("col1\tcol2\nval1\tval2\n")

        with pytest.raises(NotImplementedError):
            mixin.parse_bulk_file(dummy_path)


@pytest.mark.unit
class TestLookupGeneFromParsedData:
    """lookup_gene returns correct data when _bulk_data is populated."""

    def test_lookup_gene_from_parsed_data(self) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        mixin._bulk_data = {
            "BRCA1": {"pli": 0.99, "oe_lof": 0.12},
            "PKD1": {"pli": 0.85, "oe_lof": 0.25},
        }

        result = mixin.lookup_gene("BRCA1")
        assert result is not None
        assert result["pli"] == 0.99
        assert result["oe_lof"] == 0.12

        result_pkd1 = mixin.lookup_gene("PKD1")
        assert result_pkd1 is not None
        assert result_pkd1["pli"] == 0.85


@pytest.mark.unit
class TestLookupGeneReturnsNoneForMissing:
    """lookup_gene returns None for genes not in _bulk_data."""

    def test_lookup_gene_returns_none_for_missing(self) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        mixin._bulk_data = {
            "BRCA1": {"pli": 0.99},
        }

        result = mixin.lookup_gene("NONEXISTENT_GENE")
        assert result is None


@pytest.mark.unit
class TestIsBulkCacheFresh:
    """_is_bulk_cache_fresh returns False for non-existent files."""

    def test_is_bulk_cache_fresh_nonexistent(self) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        nonexistent = Path("/tmp/does_not_exist_abc123.tsv")

        result = mixin._is_bulk_cache_fresh(nonexistent)
        assert result is False

    def test_is_bulk_cache_fresh_existing_recent(self, tmp_path: Path) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        # Create a fresh file (just created = within TTL)
        fresh_file = tmp_path / "fresh.tsv"
        fresh_file.write_text("data")

        result = mixin._is_bulk_cache_fresh(fresh_file)
        assert result is True

    def test_is_bulk_cache_fresh_expired(self, tmp_path: Path) -> None:
        import os
        import time

        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        mixin = BulkDataSourceMixin()
        mixin.bulk_cache_ttl_hours = 0  # 0 hours = always expired

        old_file = tmp_path / "old.tsv"
        old_file.write_text("data")
        # Set mtime to 2 seconds ago to ensure it is older than 0 hours
        old_mtime = time.time() - 2
        os.utime(old_file, (old_mtime, old_mtime))

        result = mixin._is_bulk_cache_fresh(old_file)
        assert result is False


@pytest.mark.unit
class TestEnsureBulkDataLoaded:
    """ensure_bulk_data_loaded populates _bulk_data from parsed file."""

    async def test_ensure_bulk_data_loaded(self, tmp_path: Path) -> None:
        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        class TestBulkSource(BulkDataSourceMixin):
            """Concrete subclass for testing."""

            bulk_file_url = "https://example.com/data.tsv"
            bulk_cache_dir = tmp_path

            def parse_bulk_file(self, path: Path) -> dict[str, dict]:
                return {
                    "BRCA1": {"score": 0.99},
                    "PKD1": {"score": 0.85},
                }

        # Pre-create the cached file so download is skipped
        source = TestBulkSource()

        # Write a dummy file at the expected cache path
        import hashlib

        url_hash = hashlib.sha256(source.bulk_file_url.encode()).hexdigest()[:16]
        cache_file = tmp_path / f"bulk_{url_hash}.tsv"
        cache_file.write_text("dummy data")

        await source.ensure_bulk_data_loaded()

        assert source._bulk_data is not None
        assert "BRCA1" in source._bulk_data
        assert source._bulk_data["BRCA1"]["score"] == 0.99
        assert "PKD1" in source._bulk_data


@pytest.mark.unit
class TestDownloadBulkFile:
    """download_bulk_file skips download when cache is fresh."""

    async def test_download_skips_when_fresh(self, tmp_path: Path) -> None:
        import hashlib

        from app.pipeline.sources.unified.bulk_mixin import (
            BulkDataSourceMixin,
        )

        source = BulkDataSourceMixin()
        source.bulk_file_url = "https://example.com/data.tsv"
        source.bulk_cache_dir = tmp_path

        # Pre-create the cached file
        url_hash = hashlib.sha256(source.bulk_file_url.encode()).hexdigest()[:16]
        cache_file = tmp_path / f"bulk_{url_hash}.tsv"
        cache_file.write_text("cached content")

        result = await source.download_bulk_file(force=False)
        assert result == cache_file
        assert cache_file.read_text() == "cached content"
