"""Add gene annotation tables

Revision ID: c10edba96f55
Revises: 26ebdc5e2006
Create Date: 2025-08-24 22:15:57.948725

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c10edba96f55'
down_revision: Union[str, Sequence[str], None] = '26ebdc5e2006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add gene annotation tables."""
    
    # Create annotation_sources table
    op.create_table(
        'annotation_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(length=255), nullable=True),
        sa.Column('update_frequency', sa.String(length=50), nullable=True),
        sa.Column('last_update', sa.DateTime(), nullable=True),
        sa.Column('next_update', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    op.create_index(op.f('ix_annotation_sources_id'), 'annotation_sources', ['id'], unique=False)
    
    # Create gene_annotations table
    op.create_table(
        'gene_annotations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=True),
        sa.Column('annotations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('source_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gene_id', 'source', 'version', name='unique_gene_source_version')
    )
    op.create_index(op.f('ix_gene_annotations_gene_id'), 'gene_annotations', ['gene_id'], unique=False)
    op.create_index(op.f('ix_gene_annotations_id'), 'gene_annotations', ['id'], unique=False)
    op.create_index(op.f('ix_gene_annotations_source'), 'gene_annotations', ['source'], unique=False)
    # Create GIN index for JSONB queries
    op.create_index('idx_gene_annotations_jsonb', 'gene_annotations', ['annotations'], 
                    unique=False, postgresql_using='gin')
    
    # Create annotation_history table
    op.create_table(
        'annotation_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gene_id', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('operation', sa.String(length=20), nullable=True),
        sa.Column('old_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('new_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_by', sa.String(length=100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['gene_id'], ['genes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_annotation_history_gene_id'), 'annotation_history', ['gene_id'], unique=False)
    op.create_index(op.f('ix_annotation_history_id'), 'annotation_history', ['id'], unique=False)
    op.create_index(op.f('ix_annotation_history_source'), 'annotation_history', ['source'], unique=False)
    
    # Create materialized view for fast access
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS gene_annotations_summary AS
        SELECT 
            g.id as gene_id,
            g.approved_symbol,
            g.hgnc_id,
            -- HGNC annotations
            hgnc.annotations->>'ncbi_gene_id' as ncbi_gene_id,
            hgnc.annotations->'mane_select'->>'ensembl_transcript_id' as mane_select_transcript,
            hgnc.annotations->>'ensembl_gene_id' as ensembl_gene_id,
            -- gnomAD constraint scores
            (gnomad.annotations->>'pli')::FLOAT as pli,
            (gnomad.annotations->>'oe_lof')::FLOAT as oe_lof,
            (gnomad.annotations->>'oe_lof_upper')::FLOAT as oe_lof_upper,
            (gnomad.annotations->>'oe_lof_lower')::FLOAT as oe_lof_lower,
            (gnomad.annotations->>'lof_z')::FLOAT as lof_z,
            (gnomad.annotations->>'mis_z')::FLOAT as mis_z,
            (gnomad.annotations->>'syn_z')::FLOAT as syn_z,
            (gnomad.annotations->>'oe_mis')::FLOAT as oe_mis,
            (gnomad.annotations->>'oe_syn')::FLOAT as oe_syn
        FROM genes g
        LEFT JOIN LATERAL (
            SELECT annotations 
            FROM gene_annotations 
            WHERE gene_id = g.id AND source = 'hgnc' 
            ORDER BY created_at DESC 
            LIMIT 1
        ) hgnc ON true
        LEFT JOIN LATERAL (
            SELECT annotations 
            FROM gene_annotations 
            WHERE gene_id = g.id AND source = 'gnomad' 
            ORDER BY created_at DESC 
            LIMIT 1
        ) gnomad ON true;
    """)
    
    # Create unique index on materialized view
    op.execute("""
        CREATE UNIQUE INDEX idx_gene_annotations_summary_gene_id 
        ON gene_annotations_summary(gene_id);
    """)
    
    # Create index on constraint scores for filtering
    op.execute("""
        CREATE INDEX idx_gene_annotations_summary_pli 
        ON gene_annotations_summary(pli);
    """)
    
    # Insert initial annotation sources
    op.execute("""
        INSERT INTO annotation_sources (source_name, display_name, description, update_frequency, is_active, priority, config)
        VALUES 
        ('hgnc', 'HGNC', 'HUGO Gene Nomenclature Committee', 'weekly', true, 10, 
         '{"api_url": "https://rest.genenames.org", "ttl_days": 7}'::jsonb),
        ('gnomad', 'gnomAD', 'Genome Aggregation Database', 'monthly', true, 9,
         '{"api_url": "https://gnomad.broadinstitute.org/api", "version": "v4", "ttl_days": 30}'::jsonb)
    """)


def downgrade() -> None:
    """Remove gene annotation tables."""
    
    # Drop materialized view
    op.execute("DROP MATERIALIZED VIEW IF EXISTS gene_annotations_summary")
    
    # Drop tables
    op.drop_index(op.f('ix_annotation_history_source'), table_name='annotation_history')
    op.drop_index(op.f('ix_annotation_history_id'), table_name='annotation_history')
    op.drop_index(op.f('ix_annotation_history_gene_id'), table_name='annotation_history')
    op.drop_table('annotation_history')
    
    op.drop_index('idx_gene_annotations_jsonb', table_name='gene_annotations')
    op.drop_index(op.f('ix_gene_annotations_source'), table_name='gene_annotations')
    op.drop_index(op.f('ix_gene_annotations_id'), table_name='gene_annotations')
    op.drop_index(op.f('ix_gene_annotations_gene_id'), table_name='gene_annotations')
    op.drop_table('gene_annotations')
    
    op.drop_index(op.f('ix_annotation_sources_id'), table_name='annotation_sources')
    op.drop_table('annotation_sources')