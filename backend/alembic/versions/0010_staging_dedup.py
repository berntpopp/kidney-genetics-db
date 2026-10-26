"""Deduplicate gene_normalization_staging and keep it unique

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-26

Before #366 every run staged the same unresolved text again, so the dev database
holds 863 pending rows for 402 texts (HLA_A 62 times). Since #366 the staging CRUD
reuses the approved, pending or rejected record for a text; this revision cleans up
what came before and enforces that rule.

Per (original_text, source_name), the row the CRUD would reuse is kept: approved
first, then pending_review, then rejected (alphabetical, as its ORDER BY status),
the oldest id among equals. Of the other rows:
- exact unreviewed copies of the kept row are deleted (only id and timestamps differ);
- anything else, e.g. a second reviewed row, is not deleted but marked
  status 'duplicate' with is_duplicate_submission, so no review work is lost.
gene_normalization_log.staging_id references are moved to the kept row first.

Downgrade drops the index only; deleted copies held no information to restore.
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_OPEN = "('approved', 'pending_review', 'rejected')"

# Rows to fold into the row the CRUD reuses, recomputed per statement; the kept row never changes
_EXTRA = f"""
    WITH ranked AS (
        SELECT id,
               first_value(id) OVER (
                   PARTITION BY original_text, source_name ORDER BY status, id
               ) AS keep_id
        FROM gene_normalization_staging
        WHERE status IN {_OPEN}
    ), k AS (SELECT id, keep_id FROM ranked WHERE id <> keep_id)
"""


def upgrade() -> None:
    op.execute(
        _EXTRA
        + """
        UPDATE gene_normalization_log l SET staging_id = k.keep_id
        FROM k WHERE l.staging_id = k.id
        """
    )
    op.execute(
        _EXTRA
        + """
        DELETE FROM gene_normalization_staging d
        USING k, gene_normalization_staging kept
        WHERE d.id = k.id AND kept.id = k.keep_id
          AND d.status = kept.status
          AND d.reviewed_by IS NULL AND d.reviewed_at IS NULL AND d.review_notes IS NULL
          AND d.manual_approved_symbol IS NULL AND d.manual_hgnc_id IS NULL
          AND d.manual_aliases IS NULL AND d.resolved_gene_id IS NULL
          AND d.resolution_method IS NULL
          AND d.original_data IS NOT DISTINCT FROM kept.original_data
          AND d.normalization_log = kept.normalization_log
          AND d.priority_score = kept.priority_score
          AND d.requires_expert_review = kept.requires_expert_review
        """
    )
    op.execute(
        _EXTRA
        + """
        UPDATE gene_normalization_staging s
        SET status = 'duplicate', is_duplicate_submission = true
        FROM k WHERE s.id = k.id
        """
    )
    op.execute(
        f"""
        CREATE UNIQUE INDEX uq_gene_normalization_staging_open_text
        ON gene_normalization_staging (original_text, source_name)
        WHERE status IN {_OPEN}
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_gene_normalization_staging_open_text")
