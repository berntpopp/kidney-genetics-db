"""add_system_logs_table

Revision ID: 26ebdc5e2006
Revises: 001_initial_complete
Create Date: 2025-08-23 19:39:28.405605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26ebdc5e2006'
down_revision: Union[str, Sequence[str], None] = '001_initial_complete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create system_logs table for unified logging system
    op.create_table(
        'system_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('endpoint', sa.String(200), nullable=True),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(50), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),  # IPv6 support
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('extra_data', sa.JSON(), nullable=True),
        sa.Column('error_type', sa.String(100), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create performance indexes
    op.create_index('idx_system_logs_timestamp_desc', 'system_logs', ['timestamp'], postgresql_using='btree')
    op.create_index('idx_system_logs_request_id', 'system_logs', ['request_id'])
    op.create_index('idx_system_logs_level', 'system_logs', ['level'])
    op.create_index('idx_system_logs_source', 'system_logs', ['source'])
    
    # Add index for error queries
    op.create_index('idx_system_logs_error_type', 'system_logs', ['error_type'])
    
    # Add composite index for common queries
    op.create_index('idx_system_logs_timestamp_level', 'system_logs', ['timestamp', 'level'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('idx_system_logs_timestamp_level', 'system_logs')
    op.drop_index('idx_system_logs_error_type', 'system_logs')
    op.drop_index('idx_system_logs_source', 'system_logs')
    op.drop_index('idx_system_logs_level', 'system_logs')
    op.drop_index('idx_system_logs_request_id', 'system_logs')
    op.drop_index('idx_system_logs_timestamp_desc', 'system_logs')
    
    # Drop table
    op.drop_table('system_logs')
