"""fix gene_distribution_analysis matview column reference

Revision ID: 2c3fbf63d000
Revises: a9f3b2c1d4e5
Create Date: 2026-03-13 22:45:33.333712

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '2c3fbf63d000'
down_revision: Union[str, Sequence[str], None] = 'a9f3b2c1d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the broken matview so it gets recreated with corrected definition
    op.execute(text("DROP MATERIALIZED VIEW IF EXISTS gene_distribution_analysis CASCADE"))


def downgrade() -> None:
    # Drop so it can be recreated from the old code if needed
    op.execute(text("DROP MATERIALIZED VIEW IF EXISTS gene_distribution_analysis CASCADE"))
