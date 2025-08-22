"""Complete schema with tables and views

Revision ID: 2420c257f821
Revises: 
Create Date: 2025-08-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text

# Import view definitions and operations
from app.db.views import ALL_VIEWS
from app.db.alembic_ops import create_all_views, drop_all_views

# revision identifiers, used by Alembic.
revision: str = '2420c257f821'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create complete database schema including tables and views."""
    
    # ========== ENUMS ==========
    
    # Create source_status enum for data_source_progress table
    source_status = postgresql.ENUM(
        'idle', 'running', 'completed', 'failed', 'paused',
        name='source_status'
    )
    source_status.create(op.get_bind())
    
    # ========== TABLES ==========
    
    # Core tables
    op.create_table('genes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hgnc_id', sa.String(length=50), nullable=True),
        sa.Column('approved_symbol', sa.String(length=100), nullable=False),
        sa.Column('aliases', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('pipeline_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('stats', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('static_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_metadata', postgresql.JSONB(astext_type=Text()), server_default='{}', nullable=True),
        sa.Column('scoring_metadata', postgresql.JSONB(astext_type=Text()), 
                  server_default='{"type": "count", "weight": 0.5}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name'),
        sa.CheckConstraint(
            "source_type IN ('diagnostic_panel', 'manual_curation', 'literature_review', 'custom')",
            name='static_sources_type_check'
        )
    )
    
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Tables with foreign keys
    op.create_table('gene_curations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene_id', sa.Integer(), nullable=False),
        sa.Column('curation_status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('evidence_count', sa.Integer(), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=True),
        sa.Column('panelapp_panels', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('literature_refs', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('diagnostic_panels', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('hpo_terms', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('pubtator_pmids', sa.ARRAY(sa.Text()), nullable=True),
        sa.Column('omim_data', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('clinvar_data', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('constraint_scores', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('expression_data', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('evidence_score', sa.Float(), nullable=True),
        sa.Column('classification', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id')
    )
    
    op.create_table('gene_evidence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene_id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('source_detail', sa.String(length=255), nullable=True),
        sa.Column('evidence_data', postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column('evidence_date', sa.Date(), nullable=True),
        sa.Column('evidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id', 'source_name', 'source_detail', name='gene_evidence_source_idx')
    )
    
    op.create_table('static_evidence_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('evidence_name', sa.String(length=255), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('content_type', sa.String(length=50), nullable=True),
        sa.Column('upload_status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('processing_log', postgresql.JSONB(astext_type=Text()), server_default='{}', nullable=True),
        sa.Column('gene_count', sa.Integer(), nullable=True),
        sa.Column('genes_normalized', sa.Integer(), nullable=True),
        sa.Column('genes_failed', sa.Integer(), nullable=True),
        sa.Column('genes_staged', sa.Integer(), nullable=True),
        sa.Column('upload_metadata', postgresql.JSONB(astext_type=Text()), server_default='{}', nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uploaded_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'file_hash', name='unique_upload_per_source'),
        sa.CheckConstraint(
            "upload_status IN ('pending', 'processing', 'completed', 'failed', 'superseded')",
            name='upload_status_check'
        )
    )
    
    op.create_table('static_source_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=Text()), server_default='{}', nullable=True),
        sa.Column('performed_by', sa.String(length=255), nullable=True),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['static_evidence_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Additional tables not in models
    op.create_table('data_source_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('idle', 'running', 'completed', 'failed', 'paused', 
                                    name='source_status'), nullable=False, server_default='idle'),
        sa.Column('current_page', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('current_item', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('items_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_added', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_updated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('items_failed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('progress_percentage', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('current_operation', sa.String(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('rate_limit_remaining', sa.Integer(), nullable=True),
        sa.Column('rate_limit_reset', sa.DateTime(), nullable=True),
        sa.Column('last_successful_item', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    
    op.create_table('gene_normalization_staging',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('original_text', sa.String(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('original_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('normalization_log', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending_review'),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('manual_approved_symbol', sa.String(), nullable=True),
        sa.Column('manual_hgnc_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('gene_normalization_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('original_text', sa.String(), nullable=False),
        sa.Column('normalized_symbol', sa.String(), nullable=True),
        sa.Column('hgnc_id', sa.String(), nullable=True),
        sa.Column('match_type', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('match_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('cache_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(255), nullable=False),
        sa.Column('namespace', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('access_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('data_size', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_cache_entries_cache_key')
    )
    
    # ========== INDEXES ==========
    
    # Create indexes
    op.create_index(op.f('ix_genes_hgnc_id'), 'genes', ['hgnc_id'], unique=True)
    op.create_index(op.f('ix_genes_id'), 'genes', ['id'], unique=False)
    op.create_index(op.f('ix_genes_approved_symbol'), 'genes', ['approved_symbol'], unique=False)
    op.create_index(op.f('ix_pipeline_runs_id'), 'pipeline_runs', ['id'], unique=False)
    op.create_index(op.f('ix_static_sources_is_active'), 'static_sources', ['is_active'], unique=False)
    op.create_index(op.f('ix_static_sources_id'), 'static_sources', ['id'], unique=False)
    op.create_index(op.f('ix_static_sources_source_type'), 'static_sources', ['source_type'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_gene_curations_id'), 'gene_curations', ['id'], unique=False)
    op.create_index(op.f('ix_gene_curations_evidence_score'), 'gene_curations', ['evidence_score'], unique=False)
    op.create_index(op.f('ix_gene_evidence_source_name'), 'gene_evidence', ['source_name'], unique=False)
    op.create_index(op.f('ix_gene_evidence_id'), 'gene_evidence', ['id'], unique=False)
    op.create_index(op.f('ix_static_evidence_uploads_source_id'), 'static_evidence_uploads', ['source_id'], unique=False)
    op.create_index(op.f('ix_static_evidence_uploads_file_hash'), 'static_evidence_uploads', ['file_hash'], unique=False)
    op.create_index(op.f('ix_static_evidence_uploads_upload_status'), 'static_evidence_uploads', ['upload_status'], unique=False)
    op.create_index(op.f('ix_static_evidence_uploads_id'), 'static_evidence_uploads', ['id'], unique=False)
    op.create_index(op.f('ix_static_source_audit_id'), 'static_source_audit', ['id'], unique=False)
    op.create_index(op.f('ix_static_source_audit_source_id'), 'static_source_audit', ['source_id'], unique=False)
    
    # Additional indexes
    op.create_index('idx_data_source_progress_source_name', 'data_source_progress', ['source_name'])
    op.create_index('idx_cache_entries_namespace', 'cache_entries', ['namespace'])
    op.create_index('idx_cache_entries_expires_at', 'cache_entries', ['expires_at'],
                   postgresql_where=sa.text('expires_at IS NOT NULL'))
    op.create_index('idx_cache_entries_last_accessed', 'cache_entries', ['last_accessed'])
    op.create_index('idx_cache_entries_namespace_key', 'cache_entries', ['namespace', 'cache_key'])
    
    # ========== VIEWS ==========
    
    # Create all views in dependency order
    create_all_views(op, ALL_VIEWS)


def downgrade() -> None:
    """Drop complete database schema."""
    
    # Drop all views in reverse dependency order
    drop_all_views(op, ALL_VIEWS)
    
    # Drop indexes
    op.drop_index('idx_cache_entries_namespace_key', table_name='cache_entries')
    op.drop_index('idx_cache_entries_last_accessed', table_name='cache_entries')
    op.drop_index('idx_cache_entries_expires_at', table_name='cache_entries')
    op.drop_index('idx_cache_entries_namespace', table_name='cache_entries')
    op.drop_index('idx_data_source_progress_source_name', table_name='data_source_progress')
    
    op.drop_index(op.f('ix_static_source_audit_source_id'), table_name='static_source_audit')
    op.drop_index(op.f('ix_static_source_audit_id'), table_name='static_source_audit')
    op.drop_index(op.f('ix_static_evidence_uploads_id'), table_name='static_evidence_uploads')
    op.drop_index(op.f('ix_static_evidence_uploads_upload_status'), table_name='static_evidence_uploads')
    op.drop_index(op.f('ix_static_evidence_uploads_file_hash'), table_name='static_evidence_uploads')
    op.drop_index(op.f('ix_static_evidence_uploads_source_id'), table_name='static_evidence_uploads')
    op.drop_index(op.f('ix_gene_evidence_id'), table_name='gene_evidence')
    op.drop_index(op.f('ix_gene_evidence_source_name'), table_name='gene_evidence')
    op.drop_index(op.f('ix_gene_curations_evidence_score'), table_name='gene_curations')
    op.drop_index(op.f('ix_gene_curations_id'), table_name='gene_curations')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_static_sources_source_type'), table_name='static_sources')
    op.drop_index(op.f('ix_static_sources_id'), table_name='static_sources')
    op.drop_index(op.f('ix_static_sources_is_active'), table_name='static_sources')
    op.drop_index(op.f('ix_pipeline_runs_id'), table_name='pipeline_runs')
    op.drop_index(op.f('ix_genes_approved_symbol'), table_name='genes')
    op.drop_index(op.f('ix_genes_id'), table_name='genes')
    op.drop_index(op.f('ix_genes_hgnc_id'), table_name='genes')
    
    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('cache_entries')
    op.drop_table('gene_normalization_log')
    op.drop_table('gene_normalization_staging')
    op.drop_table('data_source_progress')
    op.drop_table('static_source_audit')
    op.drop_table('static_evidence_uploads')
    op.drop_table('gene_evidence')
    op.drop_table('gene_curations')
    op.drop_table('users')
    op.drop_table('static_sources')
    op.drop_table('pipeline_runs')
    op.drop_table('genes')
    
    # Drop enum
    source_status_enum = postgresql.ENUM(name='source_status')
    source_status_enum.drop(op.get_bind())