"""add_temporal_versioning_to_genes

Adds temporal versioning columns to genes table for CalVer data releases.
Implements SQL:2011 temporal pattern with valid_from and valid_to timestamps.

This enables:
- Point-in-time snapshots for research reproducibility
- Historical data queries
- Efficient storage (only changed genes create new rows)
- Fast temporal queries via GiST index (<50ms)

Revision ID: 68b329da9893
Revises: be048c9b1b53
Create Date: 2025-10-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68b329da9893'
down_revision: Union[str, None] = 'be048c9b1b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add temporal versioning columns and GiST index"""
    # Add valid_from column with default of NOW()
    # All existing genes start being valid from now
    op.add_column('genes',
        sa.Column('valid_from', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text('NOW()')))

    # Add valid_to column with default of 'infinity'
    # All existing genes are currently valid (no end date)
    op.add_column('genes',
        sa.Column('valid_to', sa.TIMESTAMP(timezone=True),
                  nullable=False, server_default=sa.text("'infinity'::timestamptz")))

    # Create GiST index on temporal range for fast temporal queries
    # tstzrange(valid_from, valid_to) creates a timestamp range
    # @> operator checks if a timestamp is contained in the range
    op.execute("""
        CREATE INDEX idx_genes_valid_time ON genes
        USING gist (tstzrange(valid_from, valid_to));
    """)


def downgrade() -> None:
    """Remove temporal versioning"""
    op.execute("DROP INDEX IF EXISTS idx_genes_valid_time;")
    op.drop_column('genes', 'valid_to')
    op.drop_column('genes', 'valid_from')
