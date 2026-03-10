"""Test backup enum values match PostgreSQL expectations."""
import pytest

from app.models.backup_job import BackupStatus, BackupTrigger


@pytest.mark.unit
class TestBackupEnums:
    """Verify enum values are lowercase (matching PostgreSQL enum type)."""

    def test_backup_status_values_are_lowercase(self):
        for member in BackupStatus:
            assert member.value == member.value.lower(), (
                f"BackupStatus.{member.name} has value '{member.value}' "
                f"— must be lowercase for PostgreSQL"
            )

    def test_backup_trigger_values_are_lowercase(self):
        for member in BackupTrigger:
            assert member.value == member.value.lower(), (
                f"BackupTrigger.{member.name} has value '{member.value}' "
                f"— must be lowercase for PostgreSQL"
            )

    def test_backup_status_column_uses_values_callable(self):
        from app.models.backup_job import BackupJob
        status_col = BackupJob.__table__.columns["status"]
        assert "completed" in status_col.type.enums, (
            "BackupJob.status ENUM must contain lowercase 'completed' — "
            "add values_callable=lambda x: [e.value for e in x]"
        )

    def test_backup_trigger_column_uses_values_callable(self):
        from app.models.backup_job import BackupJob
        trigger_col = BackupJob.__table__.columns["trigger_source"]
        assert "manual_api" in trigger_col.type.enums, (
            "BackupJob.trigger_source ENUM must contain lowercase 'manual_api' — "
            "add values_callable=lambda x: [e.value for e in x]"
        )
