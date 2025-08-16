"""Create gene_scores view and ensure all tables exist

Revision ID: 27cf0b9a6f36
Revises: c67509d91177
Create Date: 2025-08-16 17:35:03.076418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27cf0b9a6f36'
down_revision: Union[str, Sequence[str], None] = 'c67509d91177'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create gene_scores view and ensure all necessary database objects exist."""
    
    # Create gene_scores view for API performance
    op.execute("""
    CREATE OR REPLACE VIEW gene_scores AS
    SELECT 
        g.id as gene_id,
        g.approved_symbol,
        COUNT(DISTINCT ge.source_name) as source_count,
        COUNT(ge.id) as evidence_count,
        COALESCE(gc.evidence_score, 0) as raw_score,
        COALESCE(gc.evidence_score, 0) as percentage_score,
        (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) as total_active_sources,
        '{}'::jsonb as source_percentiles
    FROM genes g
    LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
    LEFT JOIN gene_curations gc ON g.id = gc.gene_id
    GROUP BY g.id, g.approved_symbol, gc.evidence_score
    ORDER BY g.approved_symbol;
    """)
    
    # Create indexes for performance if they don't exist
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_genes_hgnc_id ON genes(hgnc_id);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_genes_approved_symbol ON genes(approved_symbol);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene_id ON gene_evidence(gene_id);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_gene_evidence_source_name ON gene_evidence(source_name);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_gene_curations_gene_id ON gene_curations(gene_id);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_gene_normalization_staging_status ON gene_normalization_staging(status);
    """)
    
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_gene_normalization_staging_source ON gene_normalization_staging(source_name);
    """)


def downgrade() -> None:
    """Downgrade schema - remove gene_scores view."""
    
    # Drop view
    op.execute("DROP VIEW IF EXISTS gene_scores;")
    
    # Note: We don't drop indexes on downgrade as they don't hurt and improve performance
