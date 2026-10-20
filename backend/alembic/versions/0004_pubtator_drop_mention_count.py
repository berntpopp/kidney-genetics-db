"""Drop the sampled mention count from stored PubTator summaries (#281)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20

source_detail used to read "PubTator: N publications, M mentions", where M
was recomputed from a top-20 retained sample, not a cumulative total. The
pipeline now writes "PubTator: N publications"; this removes the misleading
suffix from existing rows. Text removal only: evidence_data is untouched and
no value is invented.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        r"""
        UPDATE gene_evidence
        SET source_detail = regexp_replace(source_detail, ', \d+ mentions$', '')
        WHERE source_name = 'PubTator'
          AND source_detail ~ ', \d+ mentions$'
        """
    )


def downgrade() -> None:
    # No-op: the removed sample count was misleading, and it remains derivable
    # from evidence_data (total_mentions) if ever needed; restoring it would
    # reintroduce the defect.
    pass
