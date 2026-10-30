"""Give DLX4 its own HGNC ID back (PHIP's HGNC:15673 was stored on it)

Revision ID: 0016
Revises: 0015
Create Date: 2026-10-30

The HGNC client's free-text "search/symbol?symbol=X" query returns PHIP first
for any X, so DLX4 (created from its alias BP1) was stored with PHIP's
HGNC:15673; PHIP's diagnostic panel evidence then attached to DLX4 through
the HGNC-ID fallback. DLX4 is HGNC:2917.

Only that exact row changes, and only while HGNC:2917 is free; elsewhere, and
on a re-run, it is a no-op. Evidence is not moved: the next DiagnosticPanels
upload of each lab that lists PHIP recreates PHIP with its own evidence.
"""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE genes SET hgnc_id = 'HGNC:2917'
        WHERE approved_symbol = 'DLX4' AND hgnc_id = 'HGNC:15673'
            AND NOT EXISTS (SELECT 1 FROM genes WHERE hgnc_id = 'HGNC:2917')
        """
    )


def downgrade() -> None:
    # No-op: restoring the wrong identifier would reintroduce the bug.
    pass
