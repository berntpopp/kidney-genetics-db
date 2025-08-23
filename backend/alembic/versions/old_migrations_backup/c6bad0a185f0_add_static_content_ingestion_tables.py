"""Add static content ingestion tables

Revision ID: c6bad0a185f0
Revises: 78f29a992e5d
Create Date: 2025-08-21

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6bad0a185f0"
down_revision: str | Sequence[str] | None = "78f29a992e5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add static content ingestion tables and views."""

    # Create static_sources table
    op.create_table(
        "static_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column(
            "scoring_metadata",
            postgresql.JSONB(),
            server_default='{"type": "count", "weight": 0.5}',
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name"),
        sa.CheckConstraint(
            "source_type IN ('diagnostic_panel', 'manual_curation', 'literature_review', 'custom')",
            name="static_sources_type_check",
        ),
    )

    # Create static_evidence_uploads table
    op.create_table(
        "static_evidence_uploads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("evidence_name", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("content_type", sa.String(50)),
        sa.Column("upload_status", sa.String(50), server_default="pending"),
        sa.Column("processing_log", postgresql.JSONB(), server_default="{}"),
        sa.Column("gene_count", sa.Integer()),
        sa.Column("genes_normalized", sa.Integer()),
        sa.Column("genes_failed", sa.Integer()),
        sa.Column("genes_staged", sa.Integer()),
        sa.Column("upload_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("uploaded_by", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["static_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "file_hash", name="unique_upload_per_source"),
        sa.CheckConstraint(
            "upload_status IN ('pending', 'processing', 'completed', 'failed', 'superseded')",
            name="upload_status_check",
        ),
    )

    # Create static_source_audit table
    op.create_table(
        "static_source_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer()),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("performed_by", sa.String(255)),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["static_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upload_id"], ["static_evidence_uploads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index("idx_static_sources_type", "static_sources", ["source_type"])
    op.create_index("idx_static_sources_active", "static_sources", ["is_active"])
    op.create_index("idx_uploads_source_id", "static_evidence_uploads", ["source_id"])
    op.create_index("idx_uploads_status", "static_evidence_uploads", ["upload_status"])
    op.create_index("idx_uploads_hash", "static_evidence_uploads", ["file_hash"])
    op.create_index("idx_audit_source_id", "static_source_audit", ["source_id"])

    # Create separate scoring views for static sources
    op.execute("""
        -- Count evidence for static sources
        CREATE VIEW static_evidence_counts AS
        SELECT
            ge.id as evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.id as source_id,
            CASE
                WHEN ss.scoring_metadata->>'field' IS NOT NULL
                     AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                    jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))
                ELSE 1
            END as source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)

    op.execute("""
        -- Scoring for static sources (separate from main evidence scoring)
        CREATE VIEW static_evidence_scores AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.display_name as source_display_name,
            CASE
                -- Count-based scoring
                WHEN ss.scoring_metadata->>'type' = 'count' THEN
                    CASE
                        WHEN ss.scoring_metadata->>'field' IS NOT NULL
                             AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                            LEAST(
                                jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))::float
                                / 10.0 * COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5),
                                1.0
                            )
                        ELSE COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5)
                    END

                -- Classification-based scoring
                WHEN ss.scoring_metadata->>'type' = 'classification'
                     AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        (ss.scoring_metadata->'weight_map' ->>
                            (ge.evidence_data->>(ss.scoring_metadata->>'field'))
                        )::numeric,
                        0.3
                    )

                -- Fixed scoring
                WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                    COALESCE((ss.scoring_metadata->>'score')::numeric, 0.5)

                ELSE 0.5
            END AS normalized_score
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)


def downgrade() -> None:
    """Remove static content ingestion tables and views."""

    # Drop views
    op.execute("DROP VIEW IF EXISTS static_evidence_scores")
    op.execute("DROP VIEW IF EXISTS static_evidence_counts")

    # Drop indexes
    op.drop_index("idx_audit_source_id")
    op.drop_index("idx_uploads_hash")
    op.drop_index("idx_uploads_status")
    op.drop_index("idx_uploads_source_id")
    op.drop_index("idx_static_sources_active")
    op.drop_index("idx_static_sources_type")

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table("static_source_audit")
    op.drop_table("static_evidence_uploads")
    op.drop_table("static_sources")
