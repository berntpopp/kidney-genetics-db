"""Merge migrations

Revision ID: 5e5f74345f03
Revises: 2b9ab9b60926, add_percentile_views
Create Date: 2025-08-16 14:46:09.685756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e5f74345f03'
down_revision: Union[str, Sequence[str], None] = ('2b9ab9b60926', 'add_percentile_views')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
