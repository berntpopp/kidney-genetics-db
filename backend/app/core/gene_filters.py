"""
Centralized gene filtering logic.

Provides consistent filtering across all endpoints that return gene counts or gene lists.
Ensures dashboard statistics, gene lists, and all other endpoints respect the same
filtering configuration without requiring manual coordination.
"""

from app.core.datasource_config import API_DEFAULTS_CONFIG


def should_hide_zero_scores(explicit_value: bool | None = None) -> bool:
    """
    Determine whether to hide genes with evidence_score=0.

    Args:
        explicit_value: If provided, uses this value. If None, uses config default.

    Returns:
        True if zero-score genes should be hidden
    """
    if explicit_value is not None:
        return explicit_value

    return API_DEFAULTS_CONFIG.get("hide_zero_scores", True)


def get_gene_score_filter_clause(hide_zero_scores: bool | None = None) -> str:
    """
    Get WHERE clause for filtering genes by score.

    This should be used in queries that join with gene_scores table.

    Args:
        hide_zero_scores: If None, uses config default

    Returns:
        SQL WHERE clause fragment (e.g., "gs.percentage_score > 0" or "1=1")
    """
    if should_hide_zero_scores(hide_zero_scores):
        return "gs.percentage_score > 0"
    return "1=1"


def get_gene_evidence_filter_join() -> tuple[str, str]:
    """
    Get JOIN and WHERE clauses for filtering genes via gene_evidence table.

    Use this when querying gene_evidence table directly and need to respect score filter.

    Returns:
        Tuple of (join_clause, where_clause)
        - join_clause: SQL to join with gene_scores
        - where_clause: SQL WHERE condition for filtering
    """
    if should_hide_zero_scores():
        return (
            "INNER JOIN gene_scores gs ON gs.gene_id = gene_evidence.gene_id",
            "gs.percentage_score > 0"
        )
    return ("", "1=1")


def count_filtered_genes_sql() -> str:
    """
    Get SQL query to count genes respecting the filter configuration.

    Returns:
        Complete SQL query string that counts genes according to filter settings
    """
    if should_hide_zero_scores():
        return """
            SELECT COUNT(DISTINCT g.id)
            FROM genes g
            INNER JOIN gene_scores gs ON gs.gene_id = g.id
            WHERE gs.percentage_score > 0
        """
    return """
        SELECT COUNT(DISTINCT g.id)
        FROM genes g
    """


def count_filtered_genes_from_evidence_sql() -> str:
    """
    Get SQL query to count unique genes from gene_evidence table.

    Returns:
        Complete SQL query that counts genes from evidence table with filtering
    """
    if should_hide_zero_scores():
        return """
            SELECT COUNT(DISTINCT ge.gene_id)
            FROM gene_evidence ge
            INNER JOIN gene_scores gs ON gs.gene_id = ge.gene_id
            WHERE gs.percentage_score > 0
        """
    return """
        SELECT COUNT(DISTINCT gene_id)
        FROM gene_evidence
    """
