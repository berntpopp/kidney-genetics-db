"""Curated association and no-association counts on data releases

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-03

Releases now export curated data (#546); the admin releases page shows the counts.
Nullable: releases published before this have none.
"""

import sqlalchemy as sa

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None

COLUMNS = ("association_count", "no_association_count")


def upgrade() -> None:
    for name in COLUMNS:
        op.add_column("data_releases", sa.Column(name, sa.Integer(), nullable=True))


def downgrade() -> None:
    for name in COLUMNS:
        op.drop_column("data_releases", name)
