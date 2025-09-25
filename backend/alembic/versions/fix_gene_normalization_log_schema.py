"""Fix gene_normalization_log table schema

Revision ID: fix_gene_norm_log
Revises: 86bdb75bc293
Create Date: 2025-09-25 08:00:00

This migration updates the gene_normalization_log table to match the current model.
The table is empty so no data migration is needed.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'fix_gene_norm_log'
down_revision = '86bdb75bc293'
branch_labels = None
depends_on = None


def upgrade():
    """Update gene_normalization_log table structure."""

    # Drop old columns that are no longer in the model
    op.drop_column('gene_normalization_log', 'normalized_symbol')
    op.drop_column('gene_normalization_log', 'match_type')
    op.drop_column('gene_normalization_log', 'confidence_score')
    op.drop_column('gene_normalization_log', 'match_details')

    # Add new columns from the model
    op.add_column('gene_normalization_log',
        sa.Column('success', sa.Boolean(), nullable=False))

    op.add_column('gene_normalization_log',
        sa.Column('approved_symbol', sa.String(), nullable=True))

    op.add_column('gene_normalization_log',
        sa.Column('normalization_log', postgresql.JSONB(), nullable=False))

    op.add_column('gene_normalization_log',
        sa.Column('final_gene_id', sa.Integer(), nullable=True))

    op.add_column('gene_normalization_log',
        sa.Column('staging_id', sa.Integer(), nullable=True))

    op.add_column('gene_normalization_log',
        sa.Column('api_calls_made', sa.Integer(), nullable=False, server_default='0'))

    op.add_column('gene_normalization_log',
        sa.Column('processing_time_ms', sa.Integer(), nullable=True))

    # Create indexes for new columns
    op.create_index('ix_gene_normalization_log_success',
                    'gene_normalization_log', ['success'])
    op.create_index('ix_gene_normalization_log_approved_symbol',
                    'gene_normalization_log', ['approved_symbol'])
    op.create_index('ix_gene_normalization_log_created_at',
                    'gene_normalization_log', ['created_at'])


def downgrade():
    """Revert to old schema."""

    # Drop new indexes
    op.drop_index('ix_gene_normalization_log_created_at')
    op.drop_index('ix_gene_normalization_log_approved_symbol')
    op.drop_index('ix_gene_normalization_log_success')

    # Remove new columns
    op.drop_column('gene_normalization_log', 'processing_time_ms')
    op.drop_column('gene_normalization_log', 'api_calls_made')
    op.drop_column('gene_normalization_log', 'staging_id')
    op.drop_column('gene_normalization_log', 'final_gene_id')
    op.drop_column('gene_normalization_log', 'normalization_log')
    op.drop_column('gene_normalization_log', 'approved_symbol')
    op.drop_column('gene_normalization_log', 'success')

    # Add back old columns
    op.add_column('gene_normalization_log',
        sa.Column('normalized_symbol', sa.String(), nullable=True))
    op.add_column('gene_normalization_log',
        sa.Column('match_type', sa.String(), nullable=True))
    op.add_column('gene_normalization_log',
        sa.Column('confidence_score', sa.Float(), nullable=True))
    op.add_column('gene_normalization_log',
        sa.Column('match_details', postgresql.JSONB(), nullable=True))