"""add_log_retention_days_setting

Revision ID: a9f3b2c1d4e5
Revises: 57009b4faa2c
Create Date: 2026-03-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9f3b2c1d4e5"
down_revision: str | Sequence[str] | None = "57009b4faa2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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

    op.bulk_insert(
        system_settings,
        [
            {
                "key": "logging.log_retention_days",
                "value": 30,
                "value_type": "number",
                "category": "logging",
                "description": "Number of days to retain system logs before automatic cleanup",
                "default_value": 30,
                "requires_restart": False,
                "is_sensitive": False,
                "is_readonly": False,
            }
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM system_settings WHERE key = 'logging.log_retention_days'")
