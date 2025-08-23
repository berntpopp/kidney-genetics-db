"""add_gene_curation_update_trigger

Revision ID: 1913be50fe24
Revises: 3a4b5c6d7e8f
Create Date: 2025-08-18 23:00:12.734606

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1913be50fe24"
down_revision: str | Sequence[str] | None = "3a4b5c6d7e8f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add database trigger to automatically update gene_curations when evidence changes.

    This eliminates the need for a separate aggregation step and ensures
    curations are always in sync with evidence.
    """
    # Create the trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_gene_curation_on_evidence_change()
        RETURNS TRIGGER AS $$
        DECLARE
            target_gene_id INTEGER;
        BEGIN
            -- Determine which gene_id to update based on operation type
            IF TG_OP = 'DELETE' THEN
                target_gene_id := OLD.gene_id;
            ELSE
                target_gene_id := NEW.gene_id;
            END IF;

            -- Update or insert gene_curation record
            INSERT INTO gene_curations (
                gene_id,
                classification,
                evidence_score,
                evidence_count,
                source_count,
                updated_at
            )
            SELECT
                g.id,
                -- Calculate classification based on evidence score
                CASE
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.8 THEN 'definitive'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.6 THEN 'strong'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.4 THEN 'moderate'
                    WHEN COALESCE(AVG(ge.evidence_score), 0) >= 0.2 THEN 'limited'
                    ELSE 'no_evidence'
                END AS classification,
                COALESCE(AVG(ge.evidence_score), 0) AS evidence_score,
                COUNT(ge.id)::INTEGER AS evidence_count,
                COUNT(DISTINCT ge.source_name)::INTEGER AS source_count,
                NOW() AS updated_at
            FROM genes g
            LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
            WHERE g.id = target_gene_id
            GROUP BY g.id
            ON CONFLICT (gene_id)
            DO UPDATE SET
                classification = EXCLUDED.classification,
                evidence_score = EXCLUDED.evidence_score,
                evidence_count = EXCLUDED.evidence_count,
                source_count = EXCLUDED.source_count,
                updated_at = EXCLUDED.updated_at;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create the trigger
    op.execute("""
        CREATE TRIGGER update_curation_on_evidence_change
        AFTER INSERT OR UPDATE OR DELETE ON gene_evidence
        FOR EACH ROW EXECUTE FUNCTION update_gene_curation_on_evidence_change();
    """)

    # Log the trigger creation
    op.execute("""
        COMMENT ON TRIGGER update_curation_on_evidence_change ON gene_evidence
        IS 'Automatically updates gene_curations when evidence changes to maintain data consistency';
    """)


def downgrade() -> None:
    """Remove the gene curation update trigger and function."""
    # Drop the trigger first
    op.execute("""
        DROP TRIGGER IF EXISTS update_curation_on_evidence_change ON gene_evidence;
    """)

    # Drop the function
    op.execute("""
        DROP FUNCTION IF EXISTS update_gene_curation_on_evidence_change();
    """)
