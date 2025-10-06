"""add_dashboard_source_distribution_views

Adds database views for dashboard source distribution visualizations:
- source_distribution_hpo: HPO term counts per gene
- source_distribution_gencc: GenCC classification distribution
- source_distribution_clingen: ClinGen classification distribution
- source_distribution_diagnosticpanels: Diagnostic panel provider distribution
- source_distribution_panelapp: PanelApp evidence levels
- source_distribution_pubtator: PubTator publication counts

These views extract JSONB evidence_data for improved dashboard visualizations.

Revision ID: 8f42e6080805
Revises: 02bb6061236e
Create Date: 2025-10-03 19:59:17.837085

"""
from collections.abc import Sequence

from alembic import op
from app.db.views import (
    source_distribution_clingen,
    source_distribution_diagnosticpanels,
    source_distribution_gencc,
    source_distribution_hpo,
    source_distribution_panelapp,
    source_distribution_pubtator,
)

# revision identifiers, used by Alembic.
revision: str = '8f42e6080805'
down_revision: str | Sequence[str] | None = '02bb6061236e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create dashboard source distribution views."""
    op.create_view(source_distribution_hpo)
    op.create_view(source_distribution_gencc)
    op.create_view(source_distribution_clingen)
    op.create_view(source_distribution_diagnosticpanels)
    op.create_view(source_distribution_panelapp)
    op.create_view(source_distribution_pubtator)


def downgrade() -> None:
    """Drop dashboard source distribution views."""
    op.drop_view(source_distribution_pubtator)
    op.drop_view(source_distribution_panelapp)
    op.drop_view(source_distribution_diagnosticpanels)
    op.drop_view(source_distribution_clingen)
    op.drop_view(source_distribution_gencc)
    op.drop_view(source_distribution_hpo)
