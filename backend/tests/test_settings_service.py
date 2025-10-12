"""
Unit tests for SettingsService

Tests the core functionality of system settings management including:
- Settings retrieval and filtering
- Setting updates with validation
- Audit trail creation
- Statistics generation
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.settings_service import SettingsService
from app.models.system_setting import SystemSetting, SettingType, SettingCategory


class TestSettingsService:
    """Test suite for SettingsService"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = MagicMock()
        db.execute = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create a SettingsService instance with mocked dependencies"""
        return SettingsService(mock_db)

    @pytest.fixture
    def sample_setting(self):
        """Create a sample setting for testing"""
        setting = SystemSetting()
        setting.id = 1
        setting.key = "cache.default_ttl"
        setting.value = 3600
        setting.value_type = SettingType.NUMBER
        setting.category = SettingCategory.CACHE
        setting.description = "Default cache TTL in seconds"
        setting.default_value = 3600
        setting.requires_restart = False
        setting.is_sensitive = False
        setting.is_readonly = False
        setting.created_at = datetime.now(timezone.utc)
        setting.updated_at = datetime.now(timezone.utc)
        return setting

    async def test_get_all_settings(self, service, mock_db, sample_setting):
        """Test retrieving all settings"""
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [sample_setting]
        mock_db.execute.return_value = mock_result

        # Call service method
        settings = await service.get_all_settings(limit=100, offset=0)

        # Verify results
        assert len(settings) == 1
        assert settings[0]["key"] == "cache.default_ttl"
        assert settings[0]["value"] == 3600
        assert settings[0]["is_sensitive"] is False

    async def test_get_setting_by_id(self, service, mock_db, sample_setting):
        """Test retrieving a single setting by ID"""
        # Mock database query
        mock_db.get.return_value = sample_setting

        # Call service method
        setting = await service.get_setting(setting_id=1)

        # Verify results
        assert setting["key"] == "cache.default_ttl"
        assert setting["value"] == 3600
        mock_db.get.assert_called_once()

    async def test_update_setting_success(self, service, mock_db, sample_setting):
        """Test successfully updating a setting"""
        # Mock database operations
        mock_db.get.return_value = sample_setting

        # Call service method
        result = await service.update_setting(
            setting_id=1,
            new_value=7200,
            user_id=1,
            ip_address="127.0.0.1",
            change_reason="Testing update"
        )

        # Verify results
        assert result["key"] == "cache.default_ttl"
        assert result["value"] == 7200
        mock_db.commit.assert_called()

    async def test_update_setting_validation_error(self, service, mock_db, sample_setting):
        """Test setting update with invalid value type"""
        # Mock database operations
        mock_db.get.return_value = sample_setting

        # Attempt to update with wrong type
        with pytest.raises(ValueError, match="must be a number"):
            await service.update_setting(
                setting_id=1,
                new_value="invalid_string",  # Should be number
                user_id=1
            )

    async def test_update_readonly_setting(self, service, mock_db):
        """Test attempting to update a read-only setting"""
        # Create readonly setting
        readonly_setting = SystemSetting()
        readonly_setting.id = 1
        readonly_setting.key = "system.version"
        readonly_setting.value = "1.0.0"
        readonly_setting.value_type = SettingType.STRING
        readonly_setting.category = SettingCategory.FEATURES
        readonly_setting.is_readonly = True

        mock_db.get.return_value = readonly_setting

        # Attempt to update
        with pytest.raises(ValueError, match="read-only"):
            await service.update_setting(
                setting_id=1,
                new_value="2.0.0",
                user_id=1
            )

    async def test_sensitive_value_masking(self, service, mock_db):
        """Test that sensitive values are masked in responses"""
        # Create sensitive setting
        sensitive_setting = SystemSetting()
        sensitive_setting.id = 1
        sensitive_setting.key = "security.jwt_secret_key"
        sensitive_setting.value = "super-secret-key-12345"
        sensitive_setting.value_type = SettingType.STRING
        sensitive_setting.category = SettingCategory.SECURITY
        sensitive_setting.is_sensitive = True

        mock_db.get.return_value = sensitive_setting

        # Get setting
        result = await service.get_setting(setting_id=1)

        # Verify value is masked
        assert result["value"] == "***MASKED***"

    async def test_get_stats(self, service, mock_db):
        """Test retrieving settings statistics"""
        # Mock database query results
        mock_result_total = MagicMock()
        mock_result_total.scalar.return_value = 13

        mock_result_restart = MagicMock()
        mock_result_restart.scalar.return_value = 5

        mock_result_recent = MagicMock()
        mock_result_recent.scalar.return_value = 2

        # Set up mock to return different results for different queries
        mock_db.execute.side_effect = [
            mock_result_total,
            mock_result_restart,
            mock_result_recent
        ]

        # Call service method
        stats = await service.get_stats()

        # Verify results
        assert stats["total"] == 13
        assert stats["requires_restart"] == 5
        assert stats["recent_changes_24h"] == 2

    async def test_audit_trail_creation(self, service, mock_db, sample_setting):
        """Test that audit trail is created on setting update"""
        # Mock database operations
        mock_db.get.return_value = sample_setting

        # Update setting
        await service.update_setting(
            setting_id=1,
            new_value=7200,
            user_id=1,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            change_reason="Performance optimization"
        )

        # Verify audit log was added
        # This would check that the audit log entry was added to the database
        # In a real test, we'd verify the SettingAuditLog object was created
        mock_db.add.assert_called()

    async def test_category_filtering(self, service, mock_db, sample_setting):
        """Test filtering settings by category"""
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [sample_setting]
        mock_db.execute.return_value = mock_result

        # Get settings filtered by category
        settings = await service.get_all_settings(
            category=SettingCategory.CACHE,
            limit=100,
            offset=0
        )

        # Verify filtering was applied
        assert len(settings) == 1
        assert settings[0]["category"] == "cache"


@pytest.mark.asyncio
class TestSettingsIntegration:
    """Integration tests for settings management"""

    async def test_full_update_workflow(self):
        """Test complete setting update workflow with real database"""
        # This would be an integration test with a real test database
        # Testing: retrieve → validate → update → verify → check audit
        pass

    async def test_concurrent_updates(self):
        """Test handling concurrent updates to the same setting"""
        # Test that concurrent updates are handled safely
        pass

    async def test_cache_invalidation_on_update(self):
        """Test that cache is invalidated when settings are updated"""
        # Verify cache is properly cleared after update
        pass
