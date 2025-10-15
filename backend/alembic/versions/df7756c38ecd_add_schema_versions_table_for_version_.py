"""add_schema_versions_table_for_version_tracking

Revision ID: df7756c38ecd
Revises: cc1fbec614ed
Create Date: 2025-10-10 13:18:47.707077

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'df7756c38ecd'
down_revision: str | Sequence[str] | None = 'cc1fbec614ed'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema - create schema_versions table."""
    op.create_table(
        'schema_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('alembic_revision', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )
    op.create_index(op.f('ix_schema_versions_id'), 'schema_versions', ['id'], unique=False)

    # Insert initial version record
    op.execute("""
        INSERT INTO schema_versions (version, alembic_revision, description, applied_at)
        VALUES ('0.1.0', 'df7756c38ecd', 'Initial version tracking system', now())
    """)


def downgrade() -> None:
    """Downgrade schema - drop schema_versions table."""
    op.drop_index(op.f('ix_schema_versions_id'), table_name='schema_versions')
    op.drop_table('schema_versions')
