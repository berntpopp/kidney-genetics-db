"""hybrid_source_crud_foundation

Revision ID: 77c32f88d831
Revises: 8f42e6080805
Create Date: 2025-10-08 10:06:58.769046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77c32f88d831'
down_revision: Union[str, Sequence[str], None] = '8f42e6080805'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add missing columns to static_sources if they don't exist
    # Check and add display_name
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_sources' AND column_name='display_name'
            ) THEN
                ALTER TABLE static_sources ADD COLUMN display_name VARCHAR(255);
            END IF;
        END $$;
    """)

    # Check and add created_by
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_sources' AND column_name='created_by'
            ) THEN
                ALTER TABLE static_sources ADD COLUMN created_by VARCHAR(255);
            END IF;
        END $$;
    """)

    # Check and add scoring_metadata (rename from metadata if needed)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_sources' AND column_name='scoring_metadata'
            ) THEN
                ALTER TABLE static_sources ADD COLUMN scoring_metadata JSONB;
            END IF;
        END $$;
    """)

    # Check and add source_metadata
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_sources' AND column_name='source_metadata'
            ) THEN
                ALTER TABLE static_sources ADD COLUMN source_metadata JSONB;
            END IF;
        END $$;
    """)

    # Update static_evidence_uploads table to match model
    # Add evidence_name (map from file_name)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='evidence_name'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN evidence_name VARCHAR(255);
                -- Copy data from file_name if it exists
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='static_evidence_uploads' AND column_name='file_name'
                ) THEN
                    UPDATE static_evidence_uploads SET evidence_name = file_name;
                END IF;
            END IF;
        END $$;
    """)

    # Add file_hash (map from content_hash)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='file_hash'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN file_hash VARCHAR(64);
                -- Copy data from content_hash if it exists
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='static_evidence_uploads' AND column_name='content_hash'
                ) THEN
                    UPDATE static_evidence_uploads SET file_hash = content_hash;
                END IF;
            END IF;
        END $$;
    """)

    # Add original_filename (map from file_name)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='original_filename'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN original_filename VARCHAR(255);
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='static_evidence_uploads' AND column_name='file_name'
                ) THEN
                    UPDATE static_evidence_uploads SET original_filename = file_name;
                END IF;
            END IF;
        END $$;
    """)

    # Add content_type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='content_type'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN content_type VARCHAR(50);
            END IF;
        END $$;
    """)

    # Add processing_log (map from error_log)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='processing_log'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN processing_log JSONB;
            END IF;
        END $$;
    """)

    # Add gene_count (map from rows_processed)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='gene_count'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN gene_count INTEGER;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='static_evidence_uploads' AND column_name='rows_processed'
                ) THEN
                    UPDATE static_evidence_uploads SET gene_count = rows_processed;
                END IF;
            END IF;
        END $$;
    """)

    # Add genes_normalized
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='genes_normalized'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN genes_normalized INTEGER;
            END IF;
        END $$;
    """)

    # Add genes_failed (map from rows_failed)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='genes_failed'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN genes_failed INTEGER;
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='static_evidence_uploads' AND column_name='rows_failed'
                ) THEN
                    UPDATE static_evidence_uploads SET genes_failed = rows_failed;
                END IF;
            END IF;
        END $$;
    """)

    # Add genes_staged
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='genes_staged'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN genes_staged INTEGER;
            END IF;
        END $$;
    """)

    # Add upload_metadata
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='static_evidence_uploads' AND column_name='upload_metadata'
            ) THEN
                ALTER TABLE static_evidence_uploads ADD COLUMN upload_metadata JSONB;
            END IF;
        END $$;
    """)

    # 2. Add indexes for delete performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_evidence_source_detail
        ON gene_evidence(source_name, source_detail)
        WHERE source_name IN ('DiagnosticPanels', 'Literature');
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_evidence_providers_gin
        ON gene_evidence USING GIN ((evidence_data->'providers'))
        WHERE source_name = 'DiagnosticPanels';
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_gene_evidence_publications_gin
        ON gene_evidence USING GIN ((evidence_data->'publications'))
        WHERE source_name = 'Literature';
    """)

    # 3. Ensure static_sources entries exist (upsert pattern)
    op.execute("""
        INSERT INTO static_sources (
            source_type, source_name, display_name, description,
            scoring_metadata, is_active, created_by, created_at, updated_at
        )
        VALUES
            (
                'hybrid', 'DiagnosticPanels', 'Diagnostic Panels',
                'Commercial diagnostic panel evidence from providers',
                '{"type": "count_based", "weight": 1.0}'::jsonb,
                true, 'system', NOW(), NOW()
            ),
            (
                'hybrid', 'Literature', 'Literature Evidence',
                'Manually curated literature evidence',
                '{"type": "count_based", "weight": 1.0}'::jsonb,
                true, 'system', NOW(), NOW()
            )
        ON CONFLICT (source_name) DO NOTHING;
    """)

    # Note: Views v_diagnostic_panel_providers and v_literature_publications
    # are managed by the view system in app/db/views.py and will be created
    # automatically on application startup via the view registry


def downgrade() -> None:
    """Downgrade schema."""
    # Note: Views are managed by app/db/views.py and will be dropped
    # automatically by the view system

    op.execute("""
        DELETE FROM static_sources
        WHERE source_name IN ('DiagnosticPanels', 'Literature');
    """)

    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_publications_gin;")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_providers_gin;")
    op.execute("DROP INDEX IF EXISTS idx_gene_evidence_source_detail;")
