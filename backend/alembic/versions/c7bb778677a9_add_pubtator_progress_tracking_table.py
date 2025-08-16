"""Add universal data source progress tracking table

Revision ID: c7bb778677a9
Revises: c6a336ffa682
Create Date: 2025-08-16 18:39:11.829486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7bb778677a9'
down_revision: Union[str, Sequence[str], None] = 'c6a336ffa682'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create data_source_progress table for tracking real-time update progress."""
    
    # Create enum for source status (check if exists first)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE source_status AS ENUM ('idle', 'running', 'completed', 'failed', 'paused');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create the progress tracking table
    op.create_table('data_source_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('status', postgresql.ENUM('idle', 'running', 'completed', 'failed', 'paused', name='source_status', create_type=False), nullable=False, server_default='idle'),
        sa.Column('current_page', sa.Integer(), server_default='0'),
        sa.Column('total_pages', sa.Integer()),
        sa.Column('current_item', sa.Integer(), server_default='0'),
        sa.Column('total_items', sa.Integer()),
        sa.Column('items_processed', sa.Integer(), server_default='0'),
        sa.Column('items_added', sa.Integer(), server_default='0'),
        sa.Column('items_updated', sa.Integer(), server_default='0'),
        sa.Column('items_failed', sa.Integer(), server_default='0'),
        sa.Column('progress_percentage', sa.Float(), server_default='0.0'),
        sa.Column('current_operation', sa.String()),
        sa.Column('last_error', sa.Text()),
        sa.Column('metadata', sa.JSON(), server_default='{}'),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('last_update_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('estimated_completion', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name')
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_data_source_progress_source_name', 'data_source_progress', ['source_name'])
    op.create_index('idx_data_source_progress_status', 'data_source_progress', ['status'])
    op.create_index('idx_data_source_progress_last_update', 'data_source_progress', ['last_update_at'])
    
    # Initialize progress records for all known sources
    op.execute("""
        INSERT INTO data_source_progress (source_name, status, metadata)
        VALUES 
            ('PanelApp', 'idle', '{"type": "api", "auto_update": true}'),
            ('PubTator', 'idle', '{"type": "api", "auto_update": true, "batch_size": 100}'),
            ('ClinGen', 'idle', '{"type": "api", "auto_update": true}'),
            ('GenCC', 'idle', '{"type": "api", "auto_update": true}'),
            ('HPO', 'idle', '{"type": "api", "auto_update": false}'),
            ('Literature', 'idle', '{"type": "manual", "auto_update": false}'),
            ('DiagnosticPanels', 'idle', '{"type": "scraper", "auto_update": false}'),
            ('HGNC_Normalization', 'idle', '{"type": "process", "auto_update": true}'),
            ('Evidence_Aggregation', 'idle', '{"type": "process", "auto_update": true}')
        ON CONFLICT (source_name) DO NOTHING;
    """)
    
    # Create trigger to update updated_at timestamp
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            NEW.last_update_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        CREATE TRIGGER update_data_source_progress_updated_at 
        BEFORE UPDATE ON data_source_progress
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create view for real-time status dashboard
    op.execute("""
        CREATE OR REPLACE VIEW data_source_status AS
        SELECT 
            source_name,
            status,
            progress_percentage,
            current_operation,
            CASE 
                WHEN total_items > 0 THEN 
                    CONCAT(items_processed, ' / ', total_items, ' items')
                WHEN total_pages > 0 THEN 
                    CONCAT(current_page, ' / ', total_pages, ' pages')
                ELSE 
                    CONCAT(items_processed, ' items')
            END as progress_text,
            CASE 
                WHEN status = 'running' AND estimated_completion IS NOT NULL THEN
                    EXTRACT(EPOCH FROM (estimated_completion - now()))::int
                ELSE NULL
            END as seconds_remaining,
            items_added,
            items_updated,
            items_failed,
            last_error,
            last_update_at,
            CASE 
                WHEN status = 'running' THEN 
                    EXTRACT(EPOCH FROM (now() - started_at))::int
                WHEN completed_at IS NOT NULL THEN
                    EXTRACT(EPOCH FROM (completed_at - started_at))::int
                ELSE NULL
            END as duration_seconds,
            metadata
        FROM data_source_progress
        ORDER BY 
            CASE status 
                WHEN 'running' THEN 1
                WHEN 'failed' THEN 2
                WHEN 'paused' THEN 3
                WHEN 'idle' THEN 4
                WHEN 'completed' THEN 5
            END,
            source_name;
    """)


def downgrade() -> None:
    """Remove progress tracking infrastructure."""
    
    # Drop view
    op.execute("DROP VIEW IF EXISTS data_source_status;")
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_data_source_progress_updated_at ON data_source_progress;")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
    
    # Drop indexes
    op.drop_index('idx_data_source_progress_last_update', table_name='data_source_progress')
    op.drop_index('idx_data_source_progress_status', table_name='data_source_progress')
    op.drop_index('idx_data_source_progress_source_name', table_name='data_source_progress')
    
    # Drop table
    op.drop_table('data_source_progress')
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS source_status;")