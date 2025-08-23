"""Add missing columns to gene_normalization_staging table

Revision ID: 002_add_missing_columns
Revises: 001_initial_complete
Create Date: 2025-08-23 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '002_add_missing_columns'
down_revision: str | None = '001_initial_complete'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add missing columns to gene_normalization_staging table
    op.add_column('gene_normalization_staging',
        sa.Column('manual_aliases', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column('gene_normalization_staging',
        sa.Column('resolved_gene_id', sa.Integer(), nullable=True))

    op.add_column('gene_normalization_staging',
        sa.Column('resolution_method', sa.String(), nullable=True))

    op.add_column('gene_normalization_staging',
        sa.Column('priority_score', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('gene_normalization_staging',
        sa.Column('requires_expert_review', sa.Boolean(), nullable=False, server_default='false'))

    op.add_column('gene_normalization_staging',
        sa.Column('is_duplicate_submission', sa.Boolean(), nullable=False, server_default='false'))

    # Create indexes for new columns
    op.create_index('ix_gene_normalization_staging_priority_score',
                    'gene_normalization_staging', ['priority_score'], unique=False)
    op.create_index('ix_gene_normalization_staging_created_at',
                    'gene_normalization_staging', ['created_at'], unique=False)
    op.create_index('ix_gene_normalization_staging_original_text',
                    'gene_normalization_staging', ['original_text'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_gene_normalization_staging_original_text', table_name='gene_normalization_staging')
    op.drop_index('ix_gene_normalization_staging_created_at', table_name='gene_normalization_staging')
    op.drop_index('ix_gene_normalization_staging_priority_score', table_name='gene_normalization_staging')

    # Drop columns
    op.drop_column('gene_normalization_staging', 'is_duplicate_submission')
    op.drop_column('gene_normalization_staging', 'requires_expert_review')
    op.drop_column('gene_normalization_staging', 'priority_score')
    op.drop_column('gene_normalization_staging', 'resolution_method')
    op.drop_column('gene_normalization_staging', 'resolved_gene_id')
    op.drop_column('gene_normalization_staging', 'manual_aliases')
