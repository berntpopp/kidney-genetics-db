"""add_cache_entries_table

Revision ID: bc903c4012b1
Revises: 09ca10c13c4a
Create Date: 2025-08-16 22:23:36.647852

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bc903c4012b1'
down_revision: str | Sequence[str] | None = '09ca10c13c4a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create cache_entries table
    op.create_table(
        'cache_entries',
        sa.Column('id', postgresql.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('cache_key', sa.Text(), nullable=False),
        sa.Column('namespace', sa.Text(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('access_count', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('data_size', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key', name='uq_cache_entries_cache_key')
    )

    # Create indexes for performance
    op.create_index('idx_cache_entries_namespace', 'cache_entries', ['namespace'])
    op.create_index('idx_cache_entries_expires_at', 'cache_entries', ['expires_at'],
                   postgresql_where=sa.text('expires_at IS NOT NULL'))
    op.create_index('idx_cache_entries_last_accessed', 'cache_entries', ['last_accessed'])
    op.create_index('idx_cache_entries_namespace_key', 'cache_entries', ['namespace', 'cache_key'])

    # Create cache statistics view
    op.execute("""
        CREATE VIEW cache_stats AS
        SELECT
            namespace,
            COUNT(*) as total_entries,
            SUM(COALESCE(data_size, pg_column_size(data))) as total_size_bytes,
            SUM(access_count) as total_accesses,
            AVG(access_count) as avg_accesses,
            COUNT(*) FILTER (WHERE expires_at IS NULL OR expires_at > NOW()) as active_entries,
            COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at <= NOW()) as expired_entries,
            MAX(last_accessed) as last_access_time,
            MIN(created_at) as oldest_entry,
            MAX(created_at) as newest_entry
        FROM cache_entries
        GROUP BY namespace;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop cache statistics view
    op.execute("DROP VIEW IF EXISTS cache_stats;")

    # Drop indexes
    op.drop_index('idx_cache_entries_namespace_key', table_name='cache_entries')
    op.drop_index('idx_cache_entries_last_accessed', table_name='cache_entries')
    op.drop_index('idx_cache_entries_expires_at', table_name='cache_entries')
    op.drop_index('idx_cache_entries_namespace', table_name='cache_entries')

    # Drop cache_entries table
    op.drop_table('cache_entries')
