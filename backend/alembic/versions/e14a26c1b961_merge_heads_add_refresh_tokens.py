"""merge heads: add refresh_tokens

Revision ID: e14a26c1b961
Revises: 0834f2555442, 285000c93ed5
Create Date: 2026-03-13 23:13:50.968720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e14a26c1b961'
down_revision: Union[str, Sequence[str], None] = ('0834f2555442', '285000c93ed5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
