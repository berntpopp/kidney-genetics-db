"""add_genes_current_view

Adds genes_current view for querying only currently valid genes.
This view filters genes where valid_to = 'infinity', making it easy to query
the current state of the database without temporal query syntax.

Revision ID: f5ee05ff38aa
Revises: 68b329da9893
Create Date: 2025-10-03

"""
from typing import Sequence, Union

from alembic import op
from app.db.alembic_ops import create_all_views, drop_all_views
from app.db.views import genes_current


# revision identifiers, used by Alembic.
revision: str = 'f5ee05ff38aa'
down_revision: Union[str, None] = '68b329da9893'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create genes_current view"""
    op.create_view(genes_current)


def downgrade() -> None:
    """Drop genes_current view"""
    op.drop_view(genes_current)
