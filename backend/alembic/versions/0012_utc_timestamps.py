"""Store the remaining naive timestamps as timestamptz

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-27

Ten columns were TIMESTAMP WITHOUT TIME ZONE. The application writes UTC into
them, but the API then serialised them without an offset, so browsers read them
as local time (admin "Last Login" showed one hour early in CET). Every other
timestamp column is already timestamptz.

The stored values are UTC, so they are converted with AT TIME ZONE 'UTC'; the
instant is unchanged. Downgrade converts back to naive UTC.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

COLUMNS = [
    ("users", "last_login"),
    ("users", "locked_until"),
    ("users", "password_reset_expires"),
    ("pipeline_runs", "started_at"),
    ("pipeline_runs", "completed_at"),
    ("annotation_history", "changed_at"),
    ("gene_normalization_staging", "reviewed_at"),
    ("gene_normalization_staging", "created_at"),
    ("gene_normalization_staging", "updated_at"),
    ("gene_normalization_log", "created_at"),
]


def upgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITH TIME ZONE USING {column} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING {column} AT TIME ZONE 'UTC'"
        )
