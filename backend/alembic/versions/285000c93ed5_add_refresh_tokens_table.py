"""add refresh_tokens table

Revision ID: 285000c93ed5
Revises: a9f3b2c1d4e5
Create Date: 2026-03-13 23:06:18.588255

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '285000c93ed5'
down_revision: str | Sequence[str] | None = 'a9f3b2c1d4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create refresh_tokens table."""
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('family_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_refresh_tokens_family_id'),
        'refresh_tokens',
        ['family_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_refresh_tokens_token_hash'),
        'refresh_tokens',
        ['token_hash'],
        unique=True,
    )


def downgrade() -> None:
    """Drop refresh_tokens table."""
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_family_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
