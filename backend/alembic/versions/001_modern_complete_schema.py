"""Modern complete schema - BIGINT everywhere for consistency

Revision ID: 001_modern_complete
Revises: None
Create Date: 2025-09-25 10:30:00

Complete modern database schema following best practices:
- BIGINT (8 bytes) for ALL primary keys (consistency + future-proof)
- TIMESTAMP WITH TIME ZONE for all timestamps
- JSONB for all JSON data
- TEXT for variable strings
- Consistent naming conventions
- All defaults at database level

Decision: Use BIGINT everywhere for simplicity and future-proofing.
No data preservation needed - clean rebuild strategy.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.db.alembic_ops import create_all_views, drop_all_views
from app.db.views import ALL_VIEWS

revision = '001_modern_complete'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create complete modern schema with all tables."""

    # Create custom types
    op.execute("CREATE TYPE source_status AS ENUM ('idle', 'running', 'completed', 'failed', 'paused')")

    # ========================================
    # CORE TABLES
    # ========================================

    # genes table - Core gene information
    op.create_table('genes',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('hgnc_id', sa.Text(), nullable=False),
        sa.Column('approved_symbol', sa.Text(), nullable=False),
        sa.Column('approved_name', sa.Text(), nullable=False),
        sa.Column('previous_symbols', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('omim_id', sa.Text(), nullable=True),
        sa.Column('ncbi_gene_id', sa.Text(), nullable=True),
        sa.Column('ensembl_gene_id', sa.Text(), nullable=True),
        sa.Column('orphanet_id', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hgnc_id')
    )
    op.create_index('idx_genes_approved_symbol', 'genes', ['approved_symbol'])
    op.create_index('idx_genes_hgnc_id', 'genes', ['hgnc_id'])

    # users table - User management
    op.create_table('users',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('hashed_password', sa.Text(), nullable=False),
        sa.Column('full_name', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # ========================================
    # ANNOTATION TABLES
    # ========================================

    # annotation_sources table
    op.create_table('annotation_sources',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )

    # gene_annotations table
    op.create_table('gene_annotations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('gene_id', sa.BigInteger(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('annotations', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id', 'source', 'version', name='unique_gene_source_version')
    )
    op.create_index('idx_gene_annotations_gene_id', 'gene_annotations', ['gene_id'])
    op.create_index('idx_gene_annotations_source', 'gene_annotations', ['source'])
    op.create_index('idx_annotations_gin', 'gene_annotations', ['annotations'], postgresql_using='gin')

    # annotation_history table
    op.create_table('annotation_history',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('gene_annotation_id', sa.BigInteger(), nullable=False),
        sa.Column('version', sa.Text(), nullable=False),
        sa.Column('annotations', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['gene_annotation_id'], ['gene_annotations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_annotation_history_gene_annotation_id', 'annotation_history', ['gene_annotation_id'])

    # ========================================
    # CURATION TABLES
    # ========================================

    # gene_curations table
    op.create_table('gene_curations',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('gene_id', sa.BigInteger(), nullable=False),
        sa.Column('classification', sa.Text(), nullable=True),
        sa.Column('evidence_summary', sa.Text(), nullable=True),
        sa.Column('diagnostic_panels', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('panelapp_panels', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('hpo_terms', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('literature_refs', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('pubtator_pmids', postgresql.ARRAY(sa.Text()), server_default='{}', nullable=False),
        sa.Column('evidence_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('source_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('curation_status', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id')
    )
    op.create_index('idx_gene_curations_gene_id', 'gene_curations', ['gene_id'])

    # gene_evidence table
    op.create_table('gene_evidence',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('gene_id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('source_detail', sa.Text(), nullable=True),
        sa.Column('classification', sa.Text(), nullable=True),
        sa.Column('evidence_type', sa.Text(), nullable=True),
        sa.Column('evidence_score', sa.Float(), nullable=True),
        sa.Column('evidence_data', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('pubtator_pmids', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id', 'source_name', 'source_detail', name='gene_evidence_source_idx')
    )
    op.create_index('idx_gene_evidence_gene_id', 'gene_evidence', ['gene_id'])
    op.create_index('idx_gene_evidence_source', 'gene_evidence', ['source_name'])

    # ========================================
    # STAGING TABLES
    # ========================================

    # gene_normalization_staging table
    op.create_table('gene_normalization_staging',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('source_detail', sa.Text(), nullable=True),
        sa.Column('context', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.Text(), server_default='pending_review', nullable=False),
        sa.Column('resolved_gene_id', sa.BigInteger(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('is_duplicate_submission', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('requires_expert_review', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('priority_score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['resolved_gene_id'], ['genes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gene_normalization_staging_original_text', 'gene_normalization_staging', ['original_text'])
    op.create_index('idx_gene_normalization_staging_created_at', 'gene_normalization_staging', ['created_at'])
    op.create_index('idx_gene_normalization_staging_status', 'gene_normalization_staging', ['status'])

    # gene_normalization_log table
    op.create_table('gene_normalization_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('hgnc_id', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('approved_symbol', sa.Text(), nullable=True),
        sa.Column('normalization_log', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('final_gene_id', sa.BigInteger(), nullable=True),
        sa.Column('staging_id', sa.BigInteger(), nullable=True),
        sa.Column('api_calls_made', sa.Integer(), server_default='0', nullable=False),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['final_gene_id'], ['genes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['staging_id'], ['gene_normalization_staging.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_gene_normalization_log_original_text', 'gene_normalization_log', ['original_text'])
    op.create_index('idx_gene_normalization_log_hgnc_id', 'gene_normalization_log', ['hgnc_id'])
    op.create_index('idx_gene_normalization_log_success', 'gene_normalization_log', ['success'])
    op.create_index('idx_gene_normalization_log_approved_symbol', 'gene_normalization_log', ['approved_symbol'])
    op.create_index('idx_gene_normalization_log_created_at', 'gene_normalization_log', ['created_at'])

    # ========================================
    # PIPELINE TABLES
    # ========================================

    # pipeline_runs table
    op.create_table('pipeline_runs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('pipeline_name', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pipeline_runs_status', 'pipeline_runs', ['status'])
    op.create_index('idx_pipeline_runs_started_at', 'pipeline_runs', ['started_at'])

    # data_source_progress table
    op.create_table('data_source_progress',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('status', postgresql.ENUM('idle', 'running', 'completed', 'failed', 'paused', name='source_status'), server_default='idle', nullable=False),
        sa.Column('current_page', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_pages', sa.Integer(), nullable=True),
        sa.Column('current_item', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('items_processed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('items_added', sa.Integer(), server_default='0', nullable=False),
        sa.Column('items_updated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('items_failed', sa.Integer(), server_default='0', nullable=False),
        sa.Column('progress_percentage', sa.Float(), server_default='0', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_update_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('estimated_completion', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_successful_item', sa.Text(), nullable=True),
        sa.Column('rate_limit_remaining', sa.Integer(), nullable=True),
        sa.Column('rate_limit_reset', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    op.create_index('idx_data_source_progress_source_name', 'data_source_progress', ['source_name'])
    op.create_index('idx_data_source_progress_status', 'data_source_progress', ['status'])

    # ========================================
    # STATIC DATA TABLES
    # ========================================

    # static_sources table
    op.create_table('static_sources',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_name', sa.Text(), nullable=False),
        sa.Column('source_type', sa.Text(), nullable=False),
        sa.Column('version', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )

    # static_source_audit table
    op.create_table('static_source_audit',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('changes', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_static_source_audit_source_id', 'static_source_audit', ['source_id'])

    # static_evidence_uploads table
    op.create_table('static_evidence_uploads',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('source_id', sa.BigInteger(), nullable=False),
        sa.Column('file_name', sa.Text(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('content_hash', sa.Text(), nullable=True),
        sa.Column('upload_status', sa.Text(), server_default='pending', nullable=False),
        sa.Column('processing_status', sa.Text(), nullable=True),
        sa.Column('rows_processed', sa.Integer(), nullable=True),
        sa.Column('rows_failed', sa.Integer(), nullable=True),
        sa.Column('error_log', postgresql.JSONB(), nullable=True),
        sa.Column('uploaded_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_static_evidence_uploads_source_id', 'static_evidence_uploads', ['source_id'])

    # ========================================
    # CACHE & SYSTEM TABLES
    # ========================================

    # cache_entries table
    op.create_table('cache_entries',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('cache_key', sa.Text(), nullable=False),
        sa.Column('namespace', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.Column('data_size', sa.Integer(), nullable=True),
        sa.Column('access_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    op.create_index('idx_cache_entries_cache_key', 'cache_entries', ['cache_key'])
    op.create_index('idx_cache_entries_namespace', 'cache_entries', ['namespace'])
    op.create_index('idx_cache_entries_expires_at', 'cache_entries', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))
    op.create_index('idx_cache_entries_last_accessed', 'cache_entries', ['last_accessed'])
    op.create_index('idx_cache_entries_namespace_key', 'cache_entries', ['namespace', 'cache_key'])

    # system_logs table
    op.create_table('system_logs',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('level', sa.Text(), nullable=False),
        sa.Column('logger', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('request_id', sa.Text(), nullable=True),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('ip_address', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('path', sa.Text(), nullable=True),
        sa.Column('method', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Float(), nullable=True),
        sa.Column('error_type', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_system_logs_timestamp', 'system_logs', [sa.text('timestamp DESC')])
    op.create_index('idx_system_logs_level', 'system_logs', ['level'])
    op.create_index('idx_system_logs_logger', 'system_logs', ['logger'])
    op.create_index('idx_system_logs_request_id', 'system_logs', ['request_id'])
    op.create_index('idx_system_logs_user_id', 'system_logs', ['user_id'])
    op.create_index('idx_system_logs_timestamp_level', 'system_logs', [sa.text('timestamp DESC'), 'level'])

    # ========================================
    # CREATE VIEWS (using existing system)
    # ========================================
    create_all_views(op, ALL_VIEWS)


def downgrade():
    """Drop all tables and types."""

    # Drop views first
    drop_all_views(op, ALL_VIEWS)

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('system_logs')
    op.drop_table('cache_entries')
    op.drop_table('static_evidence_uploads')
    op.drop_table('static_source_audit')
    op.drop_table('static_sources')
    op.drop_table('data_source_progress')
    op.drop_table('pipeline_runs')
    op.drop_table('gene_normalization_log')
    op.drop_table('gene_normalization_staging')
    op.drop_table('gene_evidence')
    op.drop_table('gene_curations')
    op.drop_table('annotation_history')
    op.drop_table('gene_annotations')
    op.drop_table('annotation_sources')
    op.drop_table('users')
    op.drop_table('genes')

    # Drop custom types
    op.execute("DROP TYPE IF EXISTS source_status")