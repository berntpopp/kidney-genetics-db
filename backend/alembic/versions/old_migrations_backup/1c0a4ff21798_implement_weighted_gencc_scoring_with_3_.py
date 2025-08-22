"""Implement weighted GenCC scoring with 3-component formula

Revision ID: 1c0a4ff21798
Revises: 443aa8a1ddf7
Create Date: 2025-08-18 07:40:56.728630

This migration implements a sophisticated weighted scoring system for GenCC evidence
that considers both the quality and quantity of classifications, as well as the
consensus among submitters.

The new scoring formula consists of three components:
1. Quality Score (50%): Uses quadratic weighting to emphasize higher classifications
2. Quantity Score (30%): Rewards multiple submissions with diminishing returns
3. Confidence Score (20%): Measures consensus on high-quality classifications

This replaces the previous simplistic approach of only using the first classification.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '1c0a4ff21798'
down_revision: str | Sequence[str] | None = '443aa8a1ddf7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    """Implement weighted GenCC scoring with 3-component formula."""

    # Drop dependent views first (in reverse dependency order)
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_classification_weights CASCADE")

    # Recreate evidence_classification_weights with weighted GenCC scoring
    op.execute("""
        CREATE OR REPLACE VIEW evidence_classification_weights AS
        WITH gencc_weighted AS (
            -- Process GenCC evidence with weighted scoring
            SELECT
                ge.id as evidence_id,
                g.id as gene_id,
                g.approved_symbol,
                ge.source_name,
                -- Calculate weighted score for GenCC using 3-component formula
                CASE
                    WHEN jsonb_array_length(ge.evidence_data->'classifications') > 0 THEN
                        -- Component 1: Quality Score (50% weight)
                        -- Uses quadratic weighting to emphasize higher classifications
                        0.5 * (
                            SUM(
                                POWER(
                                    CASE
                                        WHEN LOWER(elem::text) = '"definitive"' THEN 1.0
                                        WHEN LOWER(elem::text) = '"strong"' THEN 0.8
                                        WHEN LOWER(elem::text) = '"moderate"' THEN 0.6
                                        WHEN LOWER(elem::text) = '"supportive"' THEN 0.5  -- Added Supportive
                                        WHEN LOWER(elem::text) = '"limited"' THEN 0.4
                                        WHEN LOWER(elem::text) = '"disputed"' THEN 0.2
                                        WHEN LOWER(elem::text) = '"refuted"' THEN 0.1
                                        ELSE 0.3
                                    END, 2
                                )
                            ) / NULLIF(
                                SUM(
                                    CASE
                                        WHEN LOWER(elem::text) = '"definitive"' THEN 1.0
                                        WHEN LOWER(elem::text) = '"strong"' THEN 0.8
                                        WHEN LOWER(elem::text) = '"moderate"' THEN 0.6
                                        WHEN LOWER(elem::text) = '"supportive"' THEN 0.5
                                        WHEN LOWER(elem::text) = '"limited"' THEN 0.4
                                        WHEN LOWER(elem::text) = '"disputed"' THEN 0.2
                                        WHEN LOWER(elem::text) = '"refuted"' THEN 0.1
                                        ELSE 0.3
                                    END
                                ), 0
                            )
                        ) +
                        -- Component 2: Quantity Score (30% weight)
                        -- Rewards multiple submissions with diminishing returns (sqrt)
                        -- Normalized to 5 as typical "good evidence" baseline
                        0.3 * LEAST(1.0, SQRT(jsonb_array_length(ge.evidence_data->'classifications')::float / 5.0)) +
                        -- Component 3: Confidence Score (20% weight)
                        -- Measures proportion of high-quality classifications (Definitive/Strong)
                        0.2 * (
                            SUM(
                                CASE
                                    WHEN LOWER(elem::text) IN ('"definitive"', '"strong"') THEN 1
                                    ELSE 0
                                END
                            )::float / NULLIF(jsonb_array_length(ge.evidence_data->'classifications'), 0)
                        )
                    ELSE 0.3  -- Default if no classifications
                END as classification_weight
            FROM gene_evidence ge
            JOIN genes g ON ge.gene_id = g.id
            CROSS JOIN LATERAL jsonb_array_elements(ge.evidence_data->'classifications') AS elem
            WHERE ge.source_name = 'GenCC'
            GROUP BY ge.id, g.id, g.approved_symbol, ge.source_name, ge.evidence_data
        ),
        clingen_weights AS (
            -- ClinGen classification weights (unchanged)
            SELECT
                ge.id as evidence_id,
                g.id as gene_id,
                g.approved_symbol,
                ge.source_name,
                CASE
                    -- Handle array format: extract first element
                    WHEN jsonb_typeof(ge.evidence_data->'classifications') = 'array' THEN
                        CASE (ge.evidence_data->'classifications'->>0)::text
                            WHEN 'Definitive' THEN 1.0
                            WHEN 'Strong' THEN 0.8
                            WHEN 'Moderate' THEN 0.6
                            WHEN 'Limited' THEN 0.4
                            WHEN 'Disputed' THEN 0.2
                            WHEN 'Refuted' THEN 0.1
                            ELSE 0.3
                        END
                    -- Fallback to old singular format if it exists
                    WHEN ge.evidence_data->>'classification' IS NOT NULL THEN
                        CASE ge.evidence_data->>'classification'
                            WHEN 'Definitive' THEN 1.0
                            WHEN 'Strong' THEN 0.8
                            WHEN 'Moderate' THEN 0.6
                            WHEN 'Limited' THEN 0.4
                            WHEN 'Disputed' THEN 0.2
                            WHEN 'Refuted' THEN 0.1
                            ELSE 0.3
                        END
                    ELSE 0.3
                END as classification_weight
            FROM gene_evidence ge
            JOIN genes g ON ge.gene_id = g.id
            WHERE ge.source_name = 'ClinGen'
        )
        -- Combine both ClinGen and GenCC weighted scores
        SELECT * FROM clingen_weights
        UNION ALL
        SELECT * FROM gencc_weighted
    """)

    # Recreate evidence_normalized_scores (unchanged, but needed for dependencies)
    op.execute("""
        CREATE OR REPLACE VIEW evidence_normalized_scores AS
        -- Count-based sources (percentile normalization)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score as normalized_score
        FROM evidence_count_percentiles

        UNION ALL

        -- Classification-based sources (weight mapping with new GenCC weights)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            classification_weight as normalized_score
        FROM evidence_classification_weights
    """)

    # Recreate gene_scores (unchanged, but needed for dependencies)
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH active_sources AS (
            SELECT COUNT(DISTINCT source_name) as total_count
            FROM gene_evidence
        ),
        gene_source_scores AS (
            SELECT
                g.id as gene_id,
                g.approved_symbol,
                g.hgnc_id,
                COUNT(DISTINCT ens.source_name) as source_count,
                COUNT(ens.*) as evidence_count,
                COALESCE(SUM(ens.normalized_score), 0) as raw_score,
                jsonb_object_agg(
                    ens.source_name,
                    ROUND(ens.normalized_score::numeric, 3)
                ) FILTER (WHERE ens.source_name IS NOT NULL) as source_scores
            FROM genes g
            LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
            GROUP BY g.id, g.approved_symbol, g.hgnc_id
        )
        SELECT
            gss.gene_id,
            gss.approved_symbol,
            gss.hgnc_id,
            gss.source_count,
            gss.evidence_count,
            gss.raw_score,
            -- Divide by total active sources in system, not evidence count
            CASE
                WHEN ac.total_count > 0 THEN
                    ROUND((gss.raw_score / ac.total_count * 100)::numeric, 2)
                ELSE 0
            END as percentage_score,
            ac.total_count as total_active_sources,
            COALESCE(gss.source_scores, '{}'::jsonb) as source_scores
        FROM gene_source_scores gss
        CROSS JOIN active_sources ac
        ORDER BY percentage_score DESC NULLS LAST, gss.approved_symbol
    """)

def downgrade() -> None:
    """Revert to simple first-classification scoring for GenCC."""

    # Drop dependent views first
    op.execute("DROP VIEW IF EXISTS gene_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_normalized_scores CASCADE")
    op.execute("DROP VIEW IF EXISTS evidence_classification_weights CASCADE")

    # Recreate with original simple GenCC scoring (from previous migration)
    op.execute("""
        CREATE OR REPLACE VIEW evidence_classification_weights AS
        SELECT
            ge.id as evidence_id,
            g.id as gene_id,
            g.approved_symbol,
            ge.source_name,
            -- Extract first classification from array and map to weight
            CASE ge.source_name
                WHEN 'ClinGen' THEN
                    CASE
                        -- Handle array format: extract first element
                        WHEN jsonb_typeof(ge.evidence_data->'classifications') = 'array' THEN
                            CASE (ge.evidence_data->'classifications'->>0)::text
                                WHEN 'Definitive' THEN 1.0
                                WHEN 'Strong' THEN 0.8
                                WHEN 'Moderate' THEN 0.6
                                WHEN 'Limited' THEN 0.4
                                WHEN 'Disputed' THEN 0.2
                                WHEN 'Refuted' THEN 0.1
                                ELSE 0.3
                            END
                        -- Fallback to old singular format if it exists
                        WHEN ge.evidence_data->>'classification' IS NOT NULL THEN
                            CASE ge.evidence_data->>'classification'
                                WHEN 'Definitive' THEN 1.0
                                WHEN 'Strong' THEN 0.8
                                WHEN 'Moderate' THEN 0.6
                                WHEN 'Limited' THEN 0.4
                                WHEN 'Disputed' THEN 0.2
                                WHEN 'Refuted' THEN 0.1
                                ELSE 0.3
                            END
                        ELSE 0.3
                    END
                WHEN 'GenCC' THEN
                    CASE
                        -- Handle array format: extract first element (case-insensitive)
                        WHEN jsonb_typeof(ge.evidence_data->'classifications') = 'array' THEN
                            CASE LOWER((ge.evidence_data->'classifications'->>0)::text)
                                WHEN 'definitive' THEN 1.0
                                WHEN 'strong' THEN 0.8
                                WHEN 'moderate' THEN 0.6
                                WHEN 'limited' THEN 0.4
                                WHEN 'disputed' THEN 0.2
                                WHEN 'refuted' THEN 0.1
                                ELSE 0.3
                            END
                        -- Fallback to old singular format if it exists (case-insensitive)
                        WHEN ge.evidence_data->>'classification' IS NOT NULL THEN
                            CASE LOWER(ge.evidence_data->>'classification')
                                WHEN 'definitive' THEN 1.0
                                WHEN 'strong' THEN 0.8
                                WHEN 'moderate' THEN 0.6
                                WHEN 'limited' THEN 0.4
                                WHEN 'disputed' THEN 0.2
                                WHEN 'refuted' THEN 0.1
                                ELSE 0.3
                            END
                        ELSE 0.3
                    END
                ELSE 0.5
            END as classification_weight
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        WHERE ge.source_name IN ('ClinGen', 'GenCC')
    """)

    # Recreate evidence_normalized_scores
    op.execute("""
        CREATE OR REPLACE VIEW evidence_normalized_scores AS
        -- Count-based sources (percentile normalization)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            percentile_score as normalized_score
        FROM evidence_count_percentiles

        UNION ALL

        -- Classification-based sources (weight mapping)
        SELECT
            evidence_id,
            gene_id,
            approved_symbol,
            source_name,
            classification_weight as normalized_score
        FROM evidence_classification_weights
    """)

    # Recreate gene_scores
    op.execute("""
        CREATE OR REPLACE VIEW gene_scores AS
        WITH active_sources AS (
            SELECT COUNT(DISTINCT source_name) as total_count
            FROM gene_evidence
        ),
        gene_source_scores AS (
            SELECT
                g.id as gene_id,
                g.approved_symbol,
                g.hgnc_id,
                COUNT(DISTINCT ens.source_name) as source_count,
                COUNT(ens.*) as evidence_count,
                COALESCE(SUM(ens.normalized_score), 0) as raw_score,
                jsonb_object_agg(
                    ens.source_name,
                    ROUND(ens.normalized_score::numeric, 3)
                ) FILTER (WHERE ens.source_name IS NOT NULL) as source_scores
            FROM genes g
            LEFT JOIN evidence_normalized_scores ens ON g.id = ens.gene_id
            GROUP BY g.id, g.approved_symbol, g.hgnc_id
        )
        SELECT
            gss.gene_id,
            gss.approved_symbol,
            gss.hgnc_id,
            gss.source_count,
            gss.evidence_count,
            gss.raw_score,
            -- Divide by total active sources in system, not evidence count
            CASE
                WHEN ac.total_count > 0 THEN
                    ROUND((gss.raw_score / ac.total_count * 100)::numeric, 2)
                ELSE 0
            END as percentage_score,
            ac.total_count as total_active_sources,
            COALESCE(gss.source_scores, '{}'::jsonb) as source_scores
        FROM gene_source_scores gss
        CROSS JOIN active_sources ac
        ORDER BY percentage_score DESC NULLS LAST, gss.approved_symbol
    """)
