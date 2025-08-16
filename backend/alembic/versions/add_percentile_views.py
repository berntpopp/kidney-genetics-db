"""Add views for automatic percentile calculation

Revision ID: add_percentile_views
Revises: 
Create Date: 2025-08-16

This creates database views that automatically calculate percentiles
using PostgreSQL window functions, matching kidney-genetics-v1's
normalize_percentile() function.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'add_percentile_views'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create view for gene evidence with percentiles calculated per source
    op.execute("""
        CREATE OR REPLACE VIEW gene_evidence_with_percentiles AS
        WITH source_counts AS (
            -- Extract counts from JSONB based on source type
            SELECT 
                ge.id,
                ge.gene_id,
                ge.source_name,
                ge.source_detail,
                ge.evidence_data,
                ge.evidence_date,
                ge.created_at,
                ge.updated_at,
                CASE 
                    WHEN ge.source_name = 'PanelApp' THEN 
                        jsonb_array_length(COALESCE(ge.evidence_data->'panels', '[]'::jsonb))
                    WHEN ge.source_name = 'PubTator' THEN 
                        COALESCE((ge.evidence_data->>'publication_count')::int, 
                                jsonb_array_length(COALESCE(ge.evidence_data->'pmids', '[]'::jsonb)))
                    WHEN ge.source_name = 'HPO' THEN 
                        jsonb_array_length(COALESCE(ge.evidence_data->'phenotypes', '[]'::jsonb)) +
                        jsonb_array_length(COALESCE(ge.evidence_data->'disease_associations', '[]'::jsonb))
                    WHEN ge.source_name = 'Literature' THEN 
                        jsonb_array_length(COALESCE(ge.evidence_data->'references', '[]'::jsonb))
                    ELSE 
                        jsonb_array_length(COALESCE(ge.evidence_data->'items', '[]'::jsonb))
                END AS source_count
            FROM gene_evidence ge
        )
        SELECT 
            sc.*,
            -- Calculate percentile using PERCENT_RANK() which matches R's rank(ties.method="average")/n()
            PERCENT_RANK() OVER (
                PARTITION BY sc.source_name 
                ORDER BY sc.source_count
            ) AS source_count_percentile
        FROM source_counts sc;
    """)
    
    # Create view for aggregated gene scores (sum of percentiles)
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH percentiles AS (
            SELECT 
                gene_id,
                source_name,
                source_count_percentile
            FROM gene_evidence_with_percentiles
        )
        SELECT 
            g.id AS gene_id,
            g.approved_symbol,
            g.hgnc_id,
            COUNT(DISTINCT p.source_name) AS source_count,
            COUNT(p.*) AS evidence_count,
            COALESCE(SUM(p.source_count_percentile), 0) AS total_score,
            -- Store individual source percentiles as JSONB
            jsonb_object_agg(
                p.source_name, 
                p.source_count_percentile
            ) FILTER (WHERE p.source_name IS NOT NULL) AS source_percentiles
        FROM genes g
        LEFT JOIN percentiles p ON g.id = p.gene_id
        GROUP BY g.id, g.approved_symbol, g.hgnc_id;
    """)
    
    # Create index on the view's gene_id for performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene_id_source 
        ON gene_evidence(gene_id, source_name);
    """)
    
    print("Created views for automatic percentile calculation")


def downgrade():
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")
    op.execute("DROP VIEW IF EXISTS gene_evidence_with_percentiles CASCADE;")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_gene_id_source;")