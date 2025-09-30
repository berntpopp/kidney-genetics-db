"""add_evidence_tiers_to_gene_scores_view

Adds evidence_tier and evidence_group fields to gene_scores view for
automated evidence classification.

Revision ID: ae289b364fa1
Revises: 001_modern_complete
Create Date: 2025-09-30 10:42:53.432432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from app.db.views import gene_scores


# revision identifiers, used by Alembic.
revision: str = 'ae289b364fa1'
down_revision: Union[str, Sequence[str], None] = '001_modern_complete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Replace gene_scores view with tier calculations."""
    # Use CREATE OR REPLACE VIEW for seamless update
    op.execute(gene_scores.replace_statement())


def downgrade() -> None:
    """Revert to previous gene_scores view (no tier fields)."""
    # Cannot easily downgrade a view change without storing the old definition
    # In practice, views are forward-only migrations
    # If needed, restore from backup or recreate manually
    pass
