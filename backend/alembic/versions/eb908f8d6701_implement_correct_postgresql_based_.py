"""Implement correct PostgreSQL-based evidence scoring system

Revision ID: eb908f8d6701
Revises: 27cf0b9a6f36
Create Date: 2025-08-16 17:48:07.511427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb908f8d6701'
down_revision: Union[str, Sequence[str], None] = '27cf0b9a6f36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Implement correct PostgreSQL-based evidence scoring system.
    
    This replaces the broken Python scoring with the correct methodology:
    - Count-based sources (PanelApp, HPO, PubTator): percentile-based scoring (0-1)
    - Classification-based sources (ClinGen, GenCC): weight-based scoring (0-1)
    - Final score: sum of normalized scores / evidence count * 100
    """
    
    # Step 1: Drop existing broken view
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")
    
    # Step 2: Create source-specific count extraction view
    op.execute("""
    CREATE OR REPLACE VIEW evidence_source_counts AS
    SELECT 
        ge.gene_id,
        ge.source_name,
        g.approved_symbol,
        g.hgnc_id,
        -- Extract count based on source type
        CASE 
            WHEN ge.source_name = 'PanelApp' THEN 
                COALESCE(jsonb_array_length(ge.evidence_data->'panels'), 0)
            WHEN ge.source_name = 'HPO' THEN 
                COALESCE(jsonb_array_length(ge.evidence_data->'phenotypes'), 0) +
                COALESCE(jsonb_array_length(ge.evidence_data->'disease_associations'), 0)
            WHEN ge.source_name = 'PubTator' THEN 
                COALESCE((ge.evidence_data->>'publication_count')::int, 
                         jsonb_array_length(ge.evidence_data->'pmids'), 0)
            WHEN ge.source_name = 'Literature' THEN 
                COALESCE(jsonb_array_length(ge.evidence_data->'references'), 0)
            ELSE 1  -- Default count for other sources
        END AS source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id;
    """)
    
    # Step 3: Create percentile calculation view for count-based sources
    op.execute("""
    CREATE OR REPLACE VIEW evidence_count_percentiles AS
    SELECT 
        gene_id,
        source_name,
        approved_symbol,
        hgnc_id,
        source_count,
        -- Calculate percentiles using PERCENT_RANK (matches R's rank/n method)
        PERCENT_RANK() OVER (
            PARTITION BY source_name 
            ORDER BY source_count
        ) AS source_percentile
    FROM evidence_source_counts
    WHERE source_name IN ('PanelApp', 'HPO', 'PubTator', 'Literature');
    """)
    
    # Step 4: Create classification weight mapping view
    op.execute("""
    CREATE OR REPLACE VIEW evidence_classification_weights AS
    SELECT 
        ge.gene_id,
        ge.source_name,
        g.approved_symbol,
        g.hgnc_id,
        -- Extract classification and map to weight
        CASE 
            WHEN ge.source_name = 'ClinGen' THEN
                CASE ge.evidence_data->>'classification'
                    WHEN 'Definitive' THEN 1.0
                    WHEN 'Strong' THEN 0.8
                    WHEN 'Moderate' THEN 0.6
                    WHEN 'Limited' THEN 0.3
                    WHEN 'Disputed' THEN 0.1
                    WHEN 'Refuted' THEN 0.0
                    WHEN 'No Evidence' THEN 0.0
                    ELSE 0.5  -- Default for unknown classifications
                END
            WHEN ge.source_name = 'GenCC' THEN
                CASE ge.evidence_data->>'classification'
                    WHEN 'Definitive' THEN 1.0
                    WHEN 'Strong' THEN 0.8
                    WHEN 'Moderate' THEN 0.6
                    WHEN 'Supportive' THEN 0.5
                    WHEN 'Limited' THEN 0.3
                    WHEN 'Disputed Evidence' THEN 0.1
                    WHEN 'No Known Disease Relationship' THEN 0.0
                    WHEN 'Refuted Evidence' THEN 0.0
                    ELSE 0.5  -- Default for unknown classifications
                END
            ELSE 0.5  -- Default for other classification sources
        END AS source_weight
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    WHERE ge.source_name IN ('ClinGen', 'GenCC');
    """)
    
    # Step 5: Combine all evidence sources with normalized scores
    op.execute("""
    CREATE OR REPLACE VIEW evidence_normalized_scores AS
    -- Count-based sources with percentiles (0-1)
    SELECT 
        gene_id,
        source_name,
        approved_symbol,
        hgnc_id,
        source_percentile AS normalized_score
    FROM evidence_count_percentiles
    
    UNION ALL
    
    -- Classification-based sources with weights (0-1)
    SELECT 
        gene_id,
        source_name,
        approved_symbol,
        hgnc_id,
        source_weight AS normalized_score
    FROM evidence_classification_weights;
    """)
    
    # Step 6: Final gene scores view (correct implementation)
    op.execute("""
    CREATE OR REPLACE VIEW gene_scores AS
    SELECT 
        g.id AS gene_id,
        g.approved_symbol,
        g.hgnc_id,
        COUNT(DISTINCT ens.source_name) AS source_count,
        COUNT(ens.*) AS evidence_count,
        -- Raw score: sum of normalized scores (0 to N where N = source count)
        COALESCE(SUM(ens.normalized_score), 0) AS raw_score,
        -- Percentage score: (sum of normalized scores / evidence count) * 100
        CASE 
            WHEN COUNT(ens.*) > 0 THEN
                ROUND((COALESCE(SUM(ens.normalized_score), 0) / COUNT(ens.*) * 100)::numeric, 2)
            ELSE 0
        END AS percentage_score,
        -- Total active sources in system
        (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) AS total_active_sources,
        -- Source breakdown for debugging
        jsonb_object_agg(
            ens.source_name, 
            ens.normalized_score
        ) AS source_percentiles
    FROM genes g
    LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
    GROUP BY g.id, g.approved_symbol, g.hgnc_id
    ORDER BY percentage_score DESC NULLS LAST, g.approved_symbol;
    """)


def downgrade() -> None:
    """Remove the PostgreSQL-based scoring views."""
    
    # Drop views in reverse order
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE;")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE;")
    op.execute("DROP VIEW IF EXISTS evidence_classification_weights CASCADE;")
    op.execute("DROP VIEW IF EXISTS evidence_count_percentiles CASCADE;")
    op.execute("DROP VIEW IF EXISTS evidence_source_counts CASCADE;")
