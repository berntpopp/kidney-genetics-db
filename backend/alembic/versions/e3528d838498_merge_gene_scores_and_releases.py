"""merge_gene_scores_and_releases

Revision ID: e3528d838498
Revises: 15ad8825b8e5, 2f6d3f0fa406
Create Date: 2025-10-03 16:35:05.946787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3528d838498'
down_revision: Union[str, Sequence[str], None] = ('15ad8825b8e5', '2f6d3f0fa406')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
