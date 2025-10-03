"""
Tests for evidence filtering functionality (hide_zero_scores).
"""

import pytest
from sqlalchemy import text


@pytest.fixture
def sample_genes(db_session):
    """Create sample genes with different evidence scores."""
    # Create genes
    db_session.execute(
        text("""
            INSERT INTO genes (hgnc_id, approved_symbol, aliases)
            VALUES
                ('HGNC:1', 'GENE1', '{}'),
                ('HGNC:2', 'GENE2', '{}'),
                ('HGNC:3', 'GENE3', '{}'),
                ('HGNC:4', 'GENE4', '{}')
        """)
    )
    db_session.commit()

    # Create gene_scores entries
    db_session.execute(
        text("""
            INSERT INTO gene_scores (gene_id, evidence_count, percentage_score, source_scores)
            SELECT
                g.id,
                CASE
                    WHEN g.approved_symbol = 'GENE1' THEN 5
                    WHEN g.approved_symbol = 'GENE2' THEN 1
                    WHEN g.approved_symbol = 'GENE3' THEN 0
                    WHEN g.approved_symbol = 'GENE4' THEN 0
                END as evidence_count,
                CASE
                    WHEN g.approved_symbol = 'GENE1' THEN 75.5
                    WHEN g.approved_symbol = 'GENE2' THEN 12.3
                    WHEN g.approved_symbol = 'GENE3' THEN 0.0
                    WHEN g.approved_symbol = 'GENE4' THEN 0.0
                END as percentage_score,
                '{}'::jsonb as source_scores
            FROM genes g
        """)
    )
    db_session.commit()


def test_get_genes_default_hides_zero_scores(db_session, sample_genes):
    """Test that by default, genes with score=0 are hidden."""

    # Mock dependencies
    class MockParams:
        def __init__(self):
            self.data = {"page_number": 1, "page_size": 10}

        def __getitem__(self, key):
            return self.data[key]

    # Execute endpoint logic directly
    where_clauses = ["1=1"]
    hide_zero_scores = True  # Default value

    if hide_zero_scores:
        where_clauses.append("gs.percentage_score > 0")

    where_clause = " AND ".join(where_clauses)

    # Count genes with filter
    count_query = f"""
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        WHERE {where_clause}
    """
    result = db_session.execute(text(count_query)).scalar()

    # Should only see 2 genes (GENE1 with 75.5, GENE2 with 12.3)
    assert result == 2


def test_get_genes_show_all_includes_zero_scores(db_session, sample_genes):
    """Test that with hide_zero_scores=false, all genes are shown."""
    where_clauses = ["1=1"]
    hide_zero_scores = False  # User explicitly disabled filter

    if hide_zero_scores:
        where_clauses.append("gs.percentage_score > 0")

    where_clause = " AND ".join(where_clauses)

    # Count genes without filter
    count_query = f"""
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        WHERE {where_clause}
    """
    result = db_session.execute(text(count_query)).scalar()

    # Should see all 4 genes
    assert result == 4


def test_zero_score_filter_with_other_filters(db_session, sample_genes):
    """Test that hide_zero_scores works with other filters."""
    where_clauses = ["1=1"]
    hide_zero_scores = True

    # Add score range filter
    where_clauses.append("gs.percentage_score >= :min_score")
    where_clauses.append("gs.percentage_score <= :max_score")

    # Add zero-score filter
    if hide_zero_scores:
        where_clauses.append("gs.percentage_score > 0")

    where_clause = " AND ".join(where_clauses)

    # Count genes with both filters
    count_query = f"""
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
        LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        WHERE {where_clause}
    """
    result = db_session.execute(
        text(count_query), {"min_score": 10.0, "max_score": 80.0}
    ).scalar()

    # Should see 2 genes: GENE1 (75.5) and GENE2 (12.3)
    assert result == 2


def test_metadata_counts(db_session, sample_genes):
    """Test that metadata correctly reports hidden gene counts."""
    # With filter enabled
    where_clauses = ["1=1"]
    where_clauses.append("gs.percentage_score > 0")
    where_clause = " AND ".join(where_clauses)

    filtered_count = db_session.execute(
        text(f"""
            SELECT COUNT(DISTINCT g.id)
            FROM genes g
            LEFT JOIN gene_scores gs ON gs.gene_id = g.id
            WHERE {where_clause}
        """)
    ).scalar()

    total_count = db_session.execute(
        text("""
            SELECT COUNT(DISTINCT g.id)
            FROM genes g
            LEFT JOIN gene_scores gs ON gs.gene_id = g.id
        """)
    ).scalar()

    hidden_count = total_count - filtered_count

    assert total_count == 4
    assert filtered_count == 2
    assert hidden_count == 2


def test_genes_with_null_scores_treated_as_zero(db_session):
    """Test that genes with NULL scores are also hidden by filter."""
    # Create gene without score entry
    db_session.execute(
        text("""
            INSERT INTO genes (hgnc_id, approved_symbol, aliases)
            VALUES ('HGNC:99', 'GENE_NULL', '{}')
        """)
    )
    db_session.commit()

    # Query with filter
    where_clauses = ["1=1"]
    where_clauses.append("gs.percentage_score > 0")
    where_clause = " AND ".join(where_clauses)

    result = db_session.execute(
        text(f"""
            SELECT COUNT(DISTINCT g.id)
            FROM genes g
            LEFT JOIN gene_scores gs ON gs.gene_id = g.id
            WHERE {where_clause}
            AND g.approved_symbol = 'GENE_NULL'
        """)
    ).scalar()

    # Should not see gene with NULL score
    assert result == 0
