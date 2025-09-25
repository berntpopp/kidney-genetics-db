"""Fix gene_normalization_staging table missing columns

Revision ID: fix_gene_staging_cols
Revises: 0801ee5fb7f9
Create Date: 2025-09-20 14:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_gene_staging_cols'
down_revision = '0801ee5fb7f9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to gene_normalization_staging table."""

    # Add missing columns that the model expects
    op.add_column('gene_normalization_staging',
        sa.Column('manual_aliases', postgresql.JSONB(), nullable=True))

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

    # Create indexes for the new columns
    op.create_index('ix_gene_normalization_staging_priority_score',
                    'gene_normalization_staging', ['priority_score'], unique=False)

    op.create_index('ix_gene_normalization_staging_resolved_gene_id',
                    'gene_normalization_staging', ['resolved_gene_id'], unique=False)


def downgrade() -> None:
    """Remove the added columns."""

    # Drop indexes first
    op.drop_index('ix_gene_normalization_staging_resolved_gene_id', table_name='gene_normalization_staging')
    op.drop_index('ix_gene_normalization_staging_priority_score', table_name='gene_normalization_staging')

    # Drop columns
    op.drop_column('gene_normalization_staging', 'is_duplicate_submission')
    op.drop_column('gene_normalization_staging', 'requires_expert_review')
    op.drop_column('gene_normalization_staging', 'priority_score')
    op.drop_column('gene_normalization_staging', 'resolution_method')
    op.drop_column('gene_normalization_staging', 'resolved_gene_id')
    op.drop_column('gene_normalization_staging', 'manual_aliases')