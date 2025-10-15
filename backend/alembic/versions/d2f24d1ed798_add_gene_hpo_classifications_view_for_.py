"""Add gene_hpo_classifications view for network coloring

Adds database view for HPO clinical classifications used in network visualization:
- gene_hpo_classifications: Extracts clinical_group, onset_group, and is_syndromic
  from HPO annotations for efficient gene-to-category mapping.

This enables network nodes to be colored by clinical classification (Cystic/Ciliopathy,
CAKUT, Glomerulopathy, etc.), age of onset, or syndromic assessment instead of just
clustering assignments.

Revision ID: d2f24d1ed798
Revises: 77c32f88d831
Create Date: 2025-10-09 10:31:23.917000

"""
from collections.abc import Sequence

from alembic import op
from app.db.views import gene_hpo_classifications

# revision identifiers, used by Alembic.
revision: str = 'd2f24d1ed798'
down_revision: str | Sequence[str] | None = '77c32f88d831'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create gene_hpo_classifications view."""
    op.create_view(gene_hpo_classifications)


def downgrade() -> None:
    """Drop gene_hpo_classifications view."""
    op.drop_view(gene_hpo_classifications)
