"""Fix annotation_sources schema to match model

Revision ID: 002_modern_complete_fixed
Revises: 001_modern_complete
Create Date: 2025-09-26 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_modern_complete_fixed'
down_revision = '001_modern_complete'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to annotation_sources table
    op.add_column('annotation_sources', sa.Column('display_name', sa.Text(), nullable=False, server_default=''))
    op.add_column('annotation_sources', sa.Column('base_url', sa.Text(), nullable=True))
    op.add_column('annotation_sources', sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.add_column('annotation_sources', sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')))
    op.add_column('annotation_sources', sa.Column('update_frequency', sa.Text(), nullable=True))
    op.add_column('annotation_sources', sa.Column('last_update', sa.DateTime(timezone=True), nullable=True))
    op.add_column('annotation_sources', sa.Column('next_update', sa.DateTime(timezone=True), nullable=True))
    op.add_column('annotation_sources', sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")))
    
    # Remove server defaults after adding columns
    op.alter_column('annotation_sources', 'display_name', server_default=None)


def downgrade():
    # Remove added columns
    op.drop_column('annotation_sources', 'config')
    op.drop_column('annotation_sources', 'next_update')
    op.drop_column('annotation_sources', 'last_update')
    op.drop_column('annotation_sources', 'update_frequency')
    op.drop_column('annotation_sources', 'priority')
    op.drop_column('annotation_sources', 'is_active')
    op.drop_column('annotation_sources', 'base_url')
    op.drop_column('annotation_sources', 'display_name')
