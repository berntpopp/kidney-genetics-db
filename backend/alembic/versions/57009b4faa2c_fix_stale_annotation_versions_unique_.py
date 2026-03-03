"""fix stale annotation versions unique constraint

Revision ID: 57009b4faa2c
Revises: a1b2c3d4e5f6
Create Date: 2026-03-03 09:44:16.606481

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "57009b4faa2c"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 1: Delete stale rows — keep only the most-recently-updated row
    # per (gene_id, source) pair.
    op.execute(
        """
        DELETE FROM gene_annotations
        WHERE id NOT IN (
            SELECT DISTINCT ON (gene_id, source) id
            FROM gene_annotations
            ORDER BY gene_id, source, updated_at DESC NULLS LAST
        )
        """
    )

    # Phase 2: Drop the old 3-column constraint
    op.drop_constraint("unique_gene_source_version", "gene_annotations", type_="unique")

    # Phase 3: Create the new 2-column constraint
    op.create_unique_constraint("unique_gene_source", "gene_annotations", ["gene_id", "source"])


def downgrade() -> None:
    op.drop_constraint("unique_gene_source", "gene_annotations", type_="unique")
    op.create_unique_constraint(
        "unique_gene_source_version", "gene_annotations", ["gene_id", "source", "version"]
    )
