"""Tests for STRING PPI auto-download capability."""

import gzip
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource


@pytest.mark.unit
class TestStringPPIDownloadAttributes:
    """Test that download URL class attributes are present and valid."""

    def test_protein_info_url_attribute(self):
        """StringPPIAnnotationSource has protein_info_url with valid STRING-DB URL."""
        assert hasattr(StringPPIAnnotationSource, "protein_info_url")
        url = StringPPIAnnotationSource.protein_info_url
        assert "stringdb-downloads.org" in url
        assert "protein.info" in url
        assert url.endswith(".gz")

    def test_physical_links_url_attribute(self):
        """StringPPIAnnotationSource has physical_links_url with valid STRING-DB URL."""
        assert hasattr(StringPPIAnnotationSource, "physical_links_url")
        url = StringPPIAnnotationSource.physical_links_url
        assert "stringdb-downloads.org" in url
        assert "physical.links" in url
        assert url.endswith(".gz")


@pytest.mark.unit
class TestEnsureDataFiles:
    """Test ensure_data_files method."""

    @pytest.fixture
    def source(self):
        """Create a StringPPIAnnotationSource with mocked session."""
        with patch.object(StringPPIAnnotationSource, "__init__", lambda self, s: None):
            src = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
            src.data_dir = Path("/tmp/test_string_data")
            src.protein_info_file = "9606.protein.info.v12.0.txt"
            src.physical_links_file = "9606.protein.physical.links.v12.0.txt"
            src.protein_info_url = StringPPIAnnotationSource.protein_info_url
            src.physical_links_url = StringPPIAnnotationSource.physical_links_url
            return src

    @pytest.mark.asyncio
    async def test_ensure_data_files_skips_when_files_exist(self, source, tmp_path):
        """ensure_data_files does nothing when both files already exist."""
        source.data_dir = tmp_path
        # Create gzipped files
        (tmp_path / (source.protein_info_file + ".gz")).write_bytes(b"\x1f\x8b" + b"\x00" * 10)
        (tmp_path / (source.physical_links_file + ".gz")).write_bytes(b"\x1f\x8b" + b"\x00" * 10)

        source._download_string_file = AsyncMock()
        await source.ensure_data_files()
        source._download_string_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_data_files_skips_when_uncompressed_exist(self, source, tmp_path):
        """ensure_data_files does nothing when uncompressed files exist."""
        source.data_dir = tmp_path
        (tmp_path / source.protein_info_file).write_text("data")
        (tmp_path / source.physical_links_file).write_text("data")

        source._download_string_file = AsyncMock()
        await source.ensure_data_files()
        source._download_string_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_data_files_downloads_when_missing(self, source, tmp_path):
        """ensure_data_files calls _download_string_file for missing files."""
        source.data_dir = tmp_path
        source._download_string_file = AsyncMock()

        await source.ensure_data_files()

        assert source._download_string_file.call_count == 2
        calls = source._download_string_file.call_args_list
        # First call: protein info URL and gz dest path
        assert "protein.info" in str(calls[0][0][0])
        assert str(calls[0][0][1]).endswith(".gz")
        # Second call: physical links URL and gz dest path
        assert "physical.links" in str(calls[1][0][0])
        assert str(calls[1][0][1]).endswith(".gz")

    @pytest.mark.asyncio
    async def test_ensure_data_files_downloads_only_missing(self, source, tmp_path):
        """ensure_data_files only downloads files that are missing."""
        source.data_dir = tmp_path
        # Create only the protein info file
        (tmp_path / (source.protein_info_file + ".gz")).write_bytes(b"\x1f\x8b" + b"\x00" * 10)

        source._download_string_file = AsyncMock()
        await source.ensure_data_files()

        assert source._download_string_file.call_count == 1
        assert "physical.links" in str(source._download_string_file.call_args_list[0][0][0])


@pytest.mark.unit
class TestDownloadStringFile:
    """Test _download_string_file method."""

    @pytest.fixture
    def source(self):
        """Create a StringPPIAnnotationSource with mocked session."""
        with patch.object(StringPPIAnnotationSource, "__init__", lambda self, s: None):
            src = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
            return src

    @pytest.mark.asyncio
    async def test_download_skips_existing_file(self, source, tmp_path):
        """_download_string_file skips download if file already exists."""
        dest = tmp_path / "existing.gz"
        dest.write_bytes(b"existing data")

        with patch("app.pipeline.sources.annotations.string_ppi.httpx") as mock_httpx:
            await source._download_string_file("http://example.com/file.gz", dest)
            mock_httpx.AsyncClient.assert_not_called()

    @pytest.mark.asyncio
    async def test_download_creates_parent_dirs(self, source, tmp_path):
        """_download_string_file creates parent directories."""
        dest = tmp_path / "sub" / "dir" / "file.gz"

        # Mock httpx streaming
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = lambda chunk_size: _async_iter([b"chunk1", b"chunk2"])

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=_async_context_manager(mock_response))

        with patch("app.pipeline.sources.annotations.string_ppi.httpx") as mock_httpx:
            mock_httpx.Timeout = MagicMock(return_value="timeout_obj")
            mock_httpx.AsyncClient = MagicMock(return_value=_async_context_manager(mock_client))
            await source._download_string_file("http://example.com/file.gz", dest)

        assert dest.parent.exists()
        assert dest.exists()
        assert dest.read_bytes() == b"chunk1chunk2"

    @pytest.mark.asyncio
    async def test_download_cleans_up_tmp_on_failure(self, source, tmp_path):
        """Failed download must not leave partial files."""
        dest = tmp_path / "file.txt.gz"
        tmp_file = dest.with_suffix(".gz.tmp")

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("fail", request=MagicMock(), response=MagicMock())
        )

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=_async_context_manager(mock_response))

        with patch("app.pipeline.sources.annotations.string_ppi.httpx") as mock_httpx:
            mock_httpx.AsyncClient = MagicMock(return_value=_async_context_manager(mock_client))
            mock_httpx.Timeout = httpx.Timeout
            mock_httpx.TransportError = httpx.TransportError
            mock_httpx.HTTPStatusError = httpx.HTTPStatusError
            with pytest.raises(httpx.HTTPStatusError):
                await source._download_string_file("https://example.com/file.gz", dest)

        assert not dest.exists()
        assert not tmp_file.exists()


@pytest.mark.unit
class TestLoadDataCallsEnsure:
    """Test that _load_data calls ensure_data_files."""

    @pytest.mark.asyncio
    async def test_load_data_calls_ensure_data_files(self):
        """_load_data calls ensure_data_files before loading files."""
        with patch.object(StringPPIAnnotationSource, "__init__", lambda self, s: None):
            src = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
            src._protein_to_gene = None  # Not loaded yet
            src.data_dir = Path("/tmp/nonexistent")
            src.protein_info_file = "9606.protein.info.v12.0.txt"
            src.physical_links_file = "9606.protein.physical.links.v12.0.txt"
            src.version = "12.0"
            src.min_string_score = 400

            src.ensure_data_files = AsyncMock()
            # Make it raise after ensure_data_files to stop execution
            src.ensure_data_files.side_effect = FileNotFoundError("stop here")

            with pytest.raises(FileNotFoundError, match="stop here"):
                await src._load_data()

            src.ensure_data_files.assert_called_once()


@pytest.mark.unit
class TestValidateDataFiles:
    """Test validate_data_files method."""

    @pytest.mark.asyncio
    async def test_validate_returns_true_when_gz_files_exist(self, tmp_path):
        """validate_data_files returns True when gzipped files exist."""
        with patch.object(StringPPIAnnotationSource, "__init__", lambda self, s: None):
            src = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
            src.data_dir = tmp_path
            src.protein_info_file = "9606.protein.info.v12.0.txt"
            src.physical_links_file = "9606.protein.physical.links.v12.0.txt"

            # Create gzipped files
            (tmp_path / "9606.protein.info.v12.0.txt.gz").write_bytes(gzip.compress(b"test data"))
            (tmp_path / "9606.protein.physical.links.v12.0.txt.gz").write_bytes(
                gzip.compress(b"test data")
            )

            result = await src.validate_data_files()
            assert result is True

    @pytest.mark.asyncio
    async def test_validate_returns_false_when_files_missing(self, tmp_path):
        """validate_data_files returns False when files are missing."""
        with patch.object(StringPPIAnnotationSource, "__init__", lambda self, s: None):
            src = StringPPIAnnotationSource.__new__(StringPPIAnnotationSource)
            src.data_dir = tmp_path
            src.protein_info_file = "9606.protein.info.v12.0.txt"
            src.physical_links_file = "9606.protein.physical.links.v12.0.txt"

            result = await src.validate_data_files()
            assert result is False


# --- Helpers for async mocking ---


class _async_context_manager:
    """Helper to create an async context manager from a value."""

    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, *args):
        pass

    def __call__(self, *args, **kwargs):
        return self


async def _async_iter(items):
    """Helper to create an async iterator from a list."""
    for item in items:
        yield item
