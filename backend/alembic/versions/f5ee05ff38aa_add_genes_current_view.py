"""add_genes_current_view

Adds genes_current view for querying only currently valid genes.
This view filters genes where valid_to = 'infinity', making it easy to query
the current state of the database without temporal query syntax.

Revision ID: f5ee05ff38aa
Revises: 68b329da9893
Create Date: 2025-10-03

"""
from collections.abc import Sequence

from alembic import op
from app.db.views import genes_current

# revision identifiers, used by Alembic.
revision: str = 'f5ee05ff38aa'
down_revision: str | None = '68b329da9893'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create genes_current view"""
    op.create_view(genes_current)


def downgrade() -> None:
    """Drop genes_current view"""
    op.drop_view(genes_current)
