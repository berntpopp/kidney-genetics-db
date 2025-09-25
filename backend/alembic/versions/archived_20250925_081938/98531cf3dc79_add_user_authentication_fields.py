"""Add user authentication fields

Revision ID: 98531cf3dc79
Revises: c10edba96f55
Create Date: 2025-08-29 23:28:46.122193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '98531cf3dc79'
down_revision: Union[str, Sequence[str], None] = 'c10edba96f55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add user authentication fields."""
    # Only add user authentication fields, skip other table modifications
    
    # Add columns with defaults for existing rows
    op.add_column('users', sa.Column('username', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('permissions', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('refresh_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=255), nullable=True))
    
    # Update existing rows with defaults
    op.execute("UPDATE users SET username = SPLIT_PART(email, '@', 1) WHERE username IS NULL")
    op.execute("UPDATE users SET role = CASE WHEN is_admin = true THEN 'admin' ELSE 'viewer' END WHERE role IS NULL")
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE users SET is_verified = true WHERE is_verified IS NULL")
    op.execute("UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL")
    
    # Now make required columns NOT NULL
    op.alter_column('users', 'username', nullable=False)
    op.alter_column('users', 'role', nullable=False)
    op.alter_column('users', 'is_active', nullable=False)
    op.alter_column('users', 'is_verified', nullable=False) 
    op.alter_column('users', 'failed_login_attempts', nullable=False)
    
    # Create indexes
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)


def downgrade() -> None:
    """Downgrade schema - Remove user authentication fields."""
    # Drop indexes
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_is_active'), table_name='users')
    
    # Drop columns
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'refresh_token')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'permissions')
    op.drop_column('users', 'role')
    op.drop_column('users', 'full_name')
    op.drop_column('users', 'username')
