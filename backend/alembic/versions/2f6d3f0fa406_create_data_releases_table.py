"""create_data_releases_table

Creates data_releases table for CalVer versioned data snapshots.
Supports research reproducibility with point-in-time exports and DOI integration.

Revision ID: 2f6d3f0fa406
Revises: f5ee05ff38aa
Create Date: 2025-10-03

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2f6d3f0fa406'
down_revision: str | None = 'f5ee05ff38aa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create data_releases table"""
    op.create_table(
        'data_releases',
        # Primary fields
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('release_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),

        # Metadata
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_by_id', sa.BigInteger(), nullable=True),

        # Statistics
        sa.Column('gene_count', sa.Integer(), nullable=True),
        sa.Column('total_evidence_count', sa.Integer(), nullable=True),

        # Export
        sa.Column('export_file_path', sa.String(length=500), nullable=True),
        sa.Column('export_checksum', sa.String(length=64), nullable=True),

        # Citation
        sa.Column('doi', sa.String(length=100), nullable=True),
        sa.Column('citation_text', sa.Text(), nullable=True),

        # Notes
        sa.Column('release_notes', sa.Text(), nullable=True),

        # Timestamps (from TimestampMixin)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['published_by_id'], ['users.id'], ),
        sa.UniqueConstraint('version')
    )

    # Create indexes
    op.create_index('ix_data_releases_id', 'data_releases', ['id'])
    op.create_index('ix_data_releases_version', 'data_releases', ['version'])
    op.create_index('ix_data_releases_status', 'data_releases', ['status'])


def downgrade() -> None:
    """Drop data_releases table"""
    op.drop_index('ix_data_releases_status', table_name='data_releases')
    op.drop_index('ix_data_releases_version', table_name='data_releases')
    op.drop_index('ix_data_releases_id', table_name='data_releases')
    op.drop_table('data_releases')
