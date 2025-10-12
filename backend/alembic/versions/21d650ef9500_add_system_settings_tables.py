"""add_system_settings_tables

Revision ID: 21d650ef9500
Revises: df7756c38ecd
Create Date: 2025-10-12 17:39:34.402164

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM, JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "21d650ef9500"
down_revision: str | Sequence[str] | None = "df7756c38ecd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Define enums with explicit lowercase values to match Python enum values
# The Python model uses: SettingType.STRING = "string", etc.
setting_type_enum = ENUM("string", "number", "boolean", "json", name="setting_type")
setting_category_enum = ENUM(
    "cache",
    "security",
    "pipeline",
    "api",
    "database",
    "backup",
    "logging",
    "features",
    name="setting_category",
)


def upgrade() -> None:
    # Enums will be created automatically by SQLAlchemy when creating tables
    # that reference them, so we don't need to create them explicitly

    # Create system_settings table
    op.create_table(
        "system_settings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", JSONB, nullable=False),
        sa.Column("value_type", setting_type_enum, nullable=False),
        sa.Column("category", setting_category_enum, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_value", JSONB, nullable=False),
        sa.Column("requires_restart", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("validation_schema", JSONB, nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_readonly", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )

    # Create indexes for system_settings
    op.create_index("idx_system_settings_category", "system_settings", ["category"])
    op.create_index("idx_system_settings_key", "system_settings", ["key"])

    # Create setting_audit_log table
    op.create_table(
        "setting_audit_log",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("setting_id", sa.BigInteger(), nullable=True),
        sa.Column("setting_key", sa.String(length=100), nullable=False),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=False),
        sa.Column("changed_by_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["setting_id"], ["system_settings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for setting_audit_log
    op.create_index("idx_setting_audit_log_setting_id", "setting_audit_log", ["setting_id"])
    op.create_index("idx_setting_audit_log_changed_at", "setting_audit_log", ["changed_at"])
    op.create_index("idx_setting_audit_log_changed_by", "setting_audit_log", ["changed_by_id"])

    # Seed initial settings
    _seed_initial_settings(op)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index("idx_setting_audit_log_changed_by", "setting_audit_log")
    op.drop_index("idx_setting_audit_log_changed_at", "setting_audit_log")
    op.drop_index("idx_setting_audit_log_setting_id", "setting_audit_log")
    op.drop_table("setting_audit_log")

    op.drop_index("idx_system_settings_key", "system_settings")
    op.drop_index("idx_system_settings_category", "system_settings")
    op.drop_table("system_settings")

    # Drop enums
    setting_category_enum.drop(op.get_bind(), checkfirst=True)
    setting_type_enum.drop(op.get_bind(), checkfirst=True)


def _seed_initial_settings(op):
    """Seed initial settings from app.core.config"""
    from sqlalchemy import column, table

    system_settings = table(
        "system_settings",
        column("key", sa.String),
        column("value", JSONB),
        column("value_type", sa.String),
        column("category", sa.String),
        column("description", sa.Text),
        column("default_value", JSONB),
        column("requires_restart", sa.Boolean),
        column("is_sensitive", sa.Boolean),
        column("is_readonly", sa.Boolean),
    )

    # Map settings from app/core/config.py
    settings_data = [
        # Cache Settings
        {
            "key": "cache.default_ttl",
            "value": 3600,
            "value_type": "number",
            "category": "cache",
            "description": "Default cache TTL in seconds",
            "default_value": 3600,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "cache.max_memory_size",
            "value": 1000,
            "value_type": "number",
            "category": "cache",
            "description": "Maximum entries in memory cache",
            "default_value": 1000,
            "requires_restart": True,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "cache.cleanup_interval",
            "value": 3600,
            "value_type": "number",
            "category": "cache",
            "description": "Cleanup expired entries interval in seconds",
            "default_value": 3600,
            "requires_restart": True,
            "is_sensitive": False,
            "is_readonly": False,
        },
        # Security Settings
        {
            "key": "security.jwt_expire_minutes",
            "value": 30,
            "value_type": "number",
            "category": "security",
            "description": "JWT access token expiration in minutes",
            "default_value": 30,
            "requires_restart": True,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "security.max_login_attempts",
            "value": 5,
            "value_type": "number",
            "category": "security",
            "description": "Maximum failed login attempts before lockout",
            "default_value": 5,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "security.account_lockout_minutes",
            "value": 15,
            "value_type": "number",
            "category": "security",
            "description": "Account lockout duration in minutes",
            "default_value": 15,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "security.jwt_secret_key",
            "value": "***PLACEHOLDER***",
            "value_type": "string",
            "category": "security",
            "description": "JWT secret key for token signing (MUST CHANGE AFTER MIGRATION)",
            "default_value": "",
            "requires_restart": True,
            "is_sensitive": True,
            "is_readonly": False,
        },
        # Pipeline Settings
        {
            "key": "pipeline.hgnc_batch_size",
            "value": 50,
            "value_type": "number",
            "category": "pipeline",
            "description": "Genes per HGNC API batch request",
            "default_value": 50,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "pipeline.hgnc_retry_attempts",
            "value": 3,
            "value_type": "number",
            "category": "pipeline",
            "description": "Retry attempts for failed HGNC requests",
            "default_value": 3,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "pipeline.hgnc_cache_enabled",
            "value": True,
            "value_type": "boolean",
            "category": "pipeline",
            "description": "Enable HGNC response caching",
            "default_value": True,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        # Backup Settings
        {
            "key": "backup.retention_days",
            "value": 7,
            "value_type": "number",
            "category": "backup",
            "description": "How long to keep backups in days",
            "default_value": 7,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        {
            "key": "backup.compression_level",
            "value": 6,
            "value_type": "number",
            "category": "backup",
            "description": "Gzip compression level (0-9)",
            "default_value": 6,
            "requires_restart": False,
            "is_sensitive": False,
            "is_readonly": False,
        },
        # Feature Flags
        {
            "key": "features.auto_update_enabled",
            "value": True,
            "value_type": "boolean",
            "category": "features",
            "description": "Enable automatic background updates",
            "default_value": True,
            "requires_restart": True,
            "is_sensitive": False,
            "is_readonly": False,
        },
    ]

    op.bulk_insert(system_settings, settings_data)
