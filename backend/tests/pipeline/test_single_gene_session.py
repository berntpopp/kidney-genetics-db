"""Tests for _update_single_source session management.

Verifies that the background task creates its own SessionLocal()
instead of receiving a db parameter, and properly cleans up on errors.
Related: GitHub issue #139 (PendingRollbackError on pipeline re-run).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestUpdateSingleSourceSession:
    """Verify _update_single_source creates and manages its own DB session."""

    @pytest.mark.asyncio
    async def test_creates_own_session(self):
        """_update_single_source must call SessionLocal() internally."""
        mock_session = MagicMock()
        mock_gene = MagicMock()
        mock_gene.id = 1
        mock_gene.approved_symbol = "PKD1"

        mock_source_instance = MagicMock()
        mock_source_instance.update_gene = AsyncMock(return_value=True)
        mock_source_class = MagicMock(return_value=mock_source_instance)

        with (
            patch(
                "app.core.database.SessionLocal",
                return_value=mock_session,
            ) as mock_session_local,
            patch("app.core.cache_service.get_cache_service") as mock_cache,
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.delete = AsyncMock()
            mock_cache.return_value = mock_cache_instance

            from app.api.endpoints.annotation_updates import _update_single_source

            await _update_single_source(mock_gene, "hgnc", mock_source_class)

            mock_session_local.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_instantiated_with_fresh_session(self):
        """The source class must be instantiated with the fresh session."""
        mock_session = MagicMock()
        mock_gene = MagicMock()
        mock_gene.id = 1
        mock_gene.approved_symbol = "PKD1"

        mock_source_instance = MagicMock()
        mock_source_instance.update_gene = AsyncMock(return_value=True)
        mock_source_class = MagicMock(return_value=mock_source_instance)

        with (
            patch(
                "app.core.database.SessionLocal",
                return_value=mock_session,
            ),
            patch("app.core.cache_service.get_cache_service") as mock_cache,
        ):
            mock_cache_instance = MagicMock()
            mock_cache_instance.delete = AsyncMock()
            mock_cache.return_value = mock_cache_instance

            from app.api.endpoints.annotation_updates import _update_single_source

            await _update_single_source(mock_gene, "hgnc", mock_source_class)

            mock_source_class.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_session_closed_on_exception(self):
        """Session must be closed even when the source update raises."""
        mock_session = MagicMock()
        mock_gene = MagicMock()
        mock_gene.id = 1
        mock_gene.approved_symbol = "PKD1"

        mock_source_instance = MagicMock()
        mock_source_instance.update_gene = AsyncMock(side_effect=RuntimeError("boom"))
        mock_source_class = MagicMock(return_value=mock_source_instance)

        with patch(
            "app.core.database.SessionLocal",
            return_value=mock_session,
        ):
            from app.api.endpoints.annotation_updates import _update_single_source

            await _update_single_source(mock_gene, "hgnc", mock_source_class)

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_called_before_close_on_exception(self):
        """On exception, db.rollback() must be called before db.close()."""
        call_order: list[str] = []
        mock_session = MagicMock()
        mock_session.rollback.side_effect = lambda: call_order.append("rollback")
        mock_session.close.side_effect = lambda: call_order.append("close")

        mock_gene = MagicMock()
        mock_gene.id = 1
        mock_gene.approved_symbol = "PKD1"

        mock_source_instance = MagicMock()
        mock_source_instance.update_gene = AsyncMock(side_effect=RuntimeError("boom"))
        mock_source_class = MagicMock(return_value=mock_source_instance)

        with patch(
            "app.core.database.SessionLocal",
            return_value=mock_session,
        ):
            from app.api.endpoints.annotation_updates import _update_single_source

            await _update_single_source(mock_gene, "hgnc", mock_source_class)

            assert call_order == ["rollback", "close"]
