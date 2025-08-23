"""Remove static ingestion tables

Revision ID: 004_remove_static_tables
Revises: 003_update_views
Create Date: 2025-08-23 11:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '004_remove_static_tables'
down_revision: str | None = '003_update_views'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove static ingestion tables that are no longer needed."""

    # Drop dependent views first
    op.execute("DROP VIEW IF EXISTS static_evidence_counts CASCADE")
    op.execute("DROP VIEW IF EXISTS static_evidence_scores CASCADE")
    print("✓ Dropped dependent views")

    # Drop audit table first (has foreign key to sources)
    op.drop_table('static_source_audit')
    print("✓ Dropped static_source_audit table")

    # Drop uploads table (has foreign key to sources)
    op.drop_table('static_evidence_uploads')
    print("✓ Dropped static_evidence_uploads table")

    # Drop sources table
    op.drop_table('static_sources')
    print("✓ Dropped static_sources table")

    print("✓ All static ingestion tables removed successfully")


def downgrade() -> None:
    """Recreate static ingestion tables (for rollback)."""

    # Recreate static_sources table
    op.create_table('static_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scoring_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    op.create_index('ix_static_sources_source_name', 'static_sources', ['source_name'])
    op.create_index('ix_static_sources_is_active', 'static_sources', ['is_active'])

    # Recreate static_evidence_uploads table
    op.create_table('static_evidence_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('evidence_name', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('file_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('upload_status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('genes_submitted', sa.Integer(), nullable=True),
        sa.Column('genes_normalized', sa.Integer(), nullable=True),
        sa.Column('genes_failed', sa.Integer(), nullable=True),
        sa.Column('evidence_created', sa.Integer(), nullable=True),
        sa.Column('evidence_updated', sa.Integer(), nullable=True),
        sa.Column('normalization_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('provider_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('uploaded_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_static_evidence_uploads_source_id', 'static_evidence_uploads', ['source_id'])
    op.create_index('ix_static_evidence_uploads_evidence_name', 'static_evidence_uploads', ['evidence_name'])
    op.create_index('ix_static_evidence_uploads_upload_status', 'static_evidence_uploads', ['upload_status'])

    # Recreate static_source_audit table
    op.create_table('static_source_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('performed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('performed_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_static_source_audit_source_id', 'static_source_audit', ['source_id'])
    op.create_index('ix_static_source_audit_action', 'static_source_audit', ['action'])
    op.create_index('ix_static_source_audit_performed_at', 'static_source_audit', ['performed_at'])

    print("✓ Static ingestion tables recreated")
