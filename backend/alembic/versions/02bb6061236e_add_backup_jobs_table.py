"""add_backup_jobs_table

Creates backup_jobs table for production-grade database backup management.
Supports automated backups, restore operations, and backup tracking with checksums.

Revision ID: 02bb6061236e
Revises: e3528d838498
Create Date: 2025-10-03 17:41:14.123543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '02bb6061236e'
down_revision: Union[str, Sequence[str], None] = 'e3528d838498'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create backup_jobs table with enums and indexes."""

    # Create enums (check if not exists)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_status AS ENUM (
                'pending',
                'running',
                'completed',
                'failed',
                'restored'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE backup_trigger AS ENUM (
                'manual_api',
                'scheduled_cron',
                'pre_restore_safety'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create backup_jobs table
    op.create_table(
        'backup_jobs',
        # Primary fields
        sa.Column('id', sa.BigInteger(), nullable=False),

        # Backup metadata
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('checksum_sha256', sa.String(length=64), nullable=True),

        # Backup options
        sa.Column('format', sa.String(length=20), server_default='custom', nullable=True),
        sa.Column('compression_level', sa.SmallInteger(), server_default='6', nullable=True),
        sa.Column('include_logs', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('include_cache', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('parallel_jobs', sa.SmallInteger(), server_default='1', nullable=True),

        # Status tracking
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'restored', name='backup_status'), server_default='pending', nullable=True),
        sa.Column('trigger_source', sa.Enum('manual_api', 'scheduled_cron', 'pre_restore_safety', name='backup_trigger'), server_default='manual_api', nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),

        # User attribution
        sa.Column('created_by_id', sa.BigInteger(), nullable=True),

        # Error tracking
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', JSONB, nullable=True),

        # Statistics
        sa.Column('database_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('tables_count', sa.Integer(), nullable=True),

        # Timestamps (from TimestampMixin pattern)
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),

        # Notes
        sa.Column('description', sa.Text(), nullable=True),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.UniqueConstraint('filename')
    )

    # Create indexes for performance
    op.create_index('ix_backup_jobs_id', 'backup_jobs', ['id'])
    op.create_index('ix_backup_jobs_status', 'backup_jobs', ['status'])
    op.create_index('ix_backup_jobs_created_at', 'backup_jobs', ['created_at'], postgresql_ops={'created_at': 'DESC'})
    op.create_index('ix_backup_jobs_trigger_source', 'backup_jobs', ['trigger_source'])

    # Partial index for completed backups with expiration
    op.create_index(
        'ix_backup_jobs_expires_at',
        'backup_jobs',
        ['expires_at'],
        postgresql_where=sa.text("status = 'completed'")
    )


def downgrade() -> None:
    """Drop backup_jobs table and enums."""

    # Drop indexes
    op.drop_index('ix_backup_jobs_expires_at', table_name='backup_jobs')
    op.drop_index('ix_backup_jobs_trigger_source', table_name='backup_jobs')
    op.drop_index('ix_backup_jobs_created_at', table_name='backup_jobs')
    op.drop_index('ix_backup_jobs_status', table_name='backup_jobs')
    op.drop_index('ix_backup_jobs_id', table_name='backup_jobs')

    # Drop table
    op.drop_table('backup_jobs')

    # Drop enums
    op.execute('DROP TYPE backup_trigger')
    op.execute('DROP TYPE backup_status')
