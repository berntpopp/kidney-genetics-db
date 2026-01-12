"""
Shadow testing endpoints for comparing old and new implementations.
These endpoints run both implementations and compare results.
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db, get_thread_pool_executor
from app.core.dependencies import get_current_user_optional
from app.core.logging import get_logger
from app.core.shadow_testing import BatchShadowTester, get_shadow_tester
from app.core.validators import SQLSafeValidator
from app.models.user import User

logger = get_logger(__name__)
router = APIRouter()


class GeneListShadowTest:
    """Shadow test for gene list endpoint."""

    def __init__(self, db: Session):
        self.db = db
        self.executor = get_thread_pool_executor()

    def old_implementation(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "approved_symbol",
        sort_order: str = "ASC",
    ) -> dict[str, Any]:
        """Original SQL query implementation."""
        # Validate inputs (old way - inline)
        if sort_order.upper() not in ("ASC", "DESC"):
            sort_order = "ASC"

        # Old complex SQL query - intentionally unsafe for shadow testing
        query = text(f"""
            SELECT
                g.id AS gene_id,
                g.hgnc_id,
                g.approved_symbol AS gene_symbol,
                g.approved_name,
                g.alias_symbols,
                g.entrez_id,
                g.ensembl_gene_id,
                g.omim_id,
                g.uniprot_ids,
                g.ccds_ids,
                g.locus_group,
                g.locus_type,
                g.location,
                g.location_sortable,
                COALESCE((
                    SELECT SUM(ces.normalized_score)
                    FROM combined_evidence_scores ces
                    WHERE ces.gene_id = g.id
                ), 0) AS total_score,
                COALESCE((
                    SELECT SUM(ces.normalized_score) /
                        (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100
                    FROM combined_evidence_scores ces
                    WHERE ces.gene_id = g.id
                ), 0) AS percentage_score,
                CASE
                    WHEN COALESCE((
                        SELECT SUM(ces.normalized_score) /
                            (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100
                        FROM combined_evidence_scores ces
                        WHERE ces.gene_id = g.id
                    ), 0) >= 80 THEN 'High'
                    WHEN COALESCE((
                        SELECT SUM(ces.normalized_score) /
                            (SELECT COUNT(DISTINCT source_name) FROM combined_evidence_scores) * 100
                        FROM combined_evidence_scores ces
                        WHERE ces.gene_id = g.id
                    ), 0) >= 50 THEN 'Medium'
                    ELSE 'Low'
                END AS classification,
                (SELECT COUNT(DISTINCT source_name)
                 FROM gene_evidence ge
                 WHERE ge.gene_id = g.id) AS source_count,
                (SELECT array_agg(DISTINCT source_name ORDER BY source_name)
                 FROM gene_evidence ge
                 WHERE ge.gene_id = g.id) AS sources,
                (SELECT COUNT(DISTINCT source)
                 FROM gene_annotations ga
                 WHERE ga.gene_id = g.id) AS annotation_count,
                (SELECT array_agg(DISTINCT source ORDER BY source)
                 FROM gene_annotations ga
                 WHERE ga.gene_id = g.id) AS annotation_sources,
                g.created_at,
                g.updated_at
            FROM genes g
            WHERE g.is_active = true
            ORDER BY {sort_by} {sort_order}
            LIMIT :limit OFFSET :offset
        """)

        result = self.db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()

        return {
            "genes": [dict(row._mapping) for row in rows],
            "total": self.db.execute(
                text("SELECT COUNT(*) FROM genes WHERE is_active = true")
            ).scalar(),
        }

    def new_implementation(
        self,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "approved_symbol",
        sort_order: str = "ASC",
    ) -> dict[str, Any]:
        """New implementation using database view."""
        # Validate inputs (new way - centralized)
        validated_column = SQLSafeValidator.validate_column(sort_by, "genes")
        validated_order = SQLSafeValidator.validate_sort_order(sort_order)

        # Simple query using view
        query = text(f"""
            SELECT * FROM gene_list_detailed
            ORDER BY {validated_column} {validated_order}
            LIMIT :limit OFFSET :offset
        """)

        result = self.db.execute(query, {"limit": limit, "offset": offset})
        rows = result.fetchall()

        return {
            "genes": [dict(row._mapping) for row in rows],
            "total": self.db.execute(text("SELECT COUNT(*) FROM gene_list_detailed")).scalar(),
        }


class AdminLogsShadowTest:
    """Shadow test for admin logs endpoint."""

    def __init__(self, db: Session):
        self.db = db

    def old_implementation(
        self, level: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """Original implementation with inline SQL."""
        # Build query dynamically
        query = "SELECT * FROM system_logs WHERE 1=1"
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if level:
            query += " AND level = :level"
            params["level"] = level.upper()

        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"

        result = self.db.execute(text(query), params)
        logs = [dict(row._mapping) for row in result]

        # Get total count
        count_query = "SELECT COUNT(*) FROM system_logs WHERE 1=1"
        count_params = {}
        if level:
            count_query += " AND level = :level"
            count_params["level"] = level.upper()

        total = self.db.execute(text(count_query), count_params).scalar()

        return {
            "logs": logs,
            "total": total,
        }

    def new_implementation(
        self, level: str | None = None, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """New implementation using view."""
        # Use view with built-in filtering
        query = text("""
            SELECT * FROM admin_logs_filtered
            WHERE (:level IS NULL OR level = :level)
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = self.db.execute(
            query, {"level": level.upper() if level else None, "limit": limit, "offset": offset}
        )
        logs = [dict(row._mapping) for row in result]

        # Get total from view
        count_query = text("""
            SELECT COUNT(*) FROM admin_logs_filtered
            WHERE (:level IS NULL OR level = :level)
        """)
        total = self.db.execute(count_query, {"level": level.upper() if level else None}).scalar()

        return {
            "logs": logs,
            "total": total,
        }


@router.post("/run-single")
async def run_single_shadow_test(
    endpoint: str = Query(..., description="Endpoint to test"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    Run a single shadow test for a specific endpoint.

    Tests both old and new implementations and compares results.
    """
    shadow_tester = get_shadow_tester()

    # Map endpoint to test class
    test_classes: dict[str, type[GeneListShadowTest] | type[AdminLogsShadowTest]] = {
        "gene_list": GeneListShadowTest,
        "admin_logs": AdminLogsShadowTest,
    }

    test_class = test_classes.get(endpoint)
    if test_class is None:
        return {"error": f"Unknown endpoint: {endpoint}"}

    # Create test instance
    test_instance: GeneListShadowTest | AdminLogsShadowTest = test_class(db)

    # Run shadow test
    result = await shadow_tester.run_shadow_test(
        endpoint=endpoint,
        old_implementation=test_instance.old_implementation,
        new_implementation=test_instance.new_implementation,
        args=(),
        kwargs={},
    )

    return {
        "endpoint": result.endpoint,
        "match": result.results_match,
        "comparison_result": result.comparison_result.value,
        "old_duration_ms": round(result.old_duration_ms, 2),
        "new_duration_ms": round(result.new_duration_ms, 2),
        "performance_ratio": round(result.performance_ratio, 2),
        "performance_improvement": f"{round((1 - result.performance_ratio) * 100, 1)}%",
        "differences": result.differences,
        "error": result.error,
    }


@router.post("/run-batch")
async def run_batch_shadow_tests(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    Run shadow tests for all configured endpoints.

    Returns summary report of all test results.
    """
    shadow_tester = get_shadow_tester()
    batch_tester = BatchShadowTester(shadow_tester)

    # Define test cases
    test_cases = []

    # Gene list test
    gene_test = GeneListShadowTest(db)
    test_cases.append(
        {
            "endpoint": "gene_list",
            "old_implementation": gene_test.old_implementation,
            "new_implementation": gene_test.new_implementation,
            "kwargs": {"limit": 10},
        }
    )

    # Admin logs test
    logs_test = AdminLogsShadowTest(db)
    test_cases.append(
        {
            "endpoint": "admin_logs",
            "old_implementation": logs_test.old_implementation,
            "new_implementation": logs_test.new_implementation,
            "kwargs": {"limit": 10},
        }
    )

    # Run all tests
    results = await batch_tester.run_batch_tests(test_cases)

    # Generate report
    report = batch_tester.generate_report(results)

    await logger.info(
        "Batch shadow test completed", summary=report["summary"], performance=report["performance"]
    )

    return report


@router.get("/results")
async def get_shadow_test_results(
    hours: int = Query(24, description="Hours of history to retrieve"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    Get historical shadow test results from monitoring.

    Retrieves metrics from the last N hours.
    """
    # This would query Prometheus or database for historical metrics
    # For now, return mock data structure
    return {
        "time_range": f"Last {hours} hours",
        "summary": {
            "total_tests": 0,
            "matches": 0,
            "mismatches": 0,
            "match_rate": 0,
        },
        "performance": {
            "avg_improvement": 0,
            "regression_count": 0,
        },
        "endpoints": {},
        "message": "Historical metrics would be retrieved from monitoring system",
    }


@router.post("/validate-migration")
async def validate_migration_readiness(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """
    Validate if the system is ready for full migration to views.

    Runs comprehensive tests and checks thresholds.
    """
    shadow_tester = get_shadow_tester()
    batch_tester = BatchShadowTester(shadow_tester)

    # Run comprehensive tests
    test_cases = []

    # Test multiple scenarios for each endpoint
    gene_test = GeneListShadowTest(db)
    for limit in [10, 100, 1000]:
        for sort_by in ["approved_symbol", "total_score", "percentage_score"]:
            test_cases.append(
                {
                    "endpoint": f"gene_list_{limit}_{sort_by}",
                    "old_implementation": gene_test.old_implementation,
                    "new_implementation": gene_test.new_implementation,
                    "kwargs": {"limit": limit, "sort_by": sort_by},
                }
            )

    results = await batch_tester.run_batch_tests(test_cases)
    report = batch_tester.generate_report(results)

    # Define migration readiness criteria
    criteria = {
        "match_rate": report["summary"]["match_rate"] >= 95,  # 95% match rate
        "performance": report["performance"]["avg_performance_ratio"] <= 1.2,  # Max 20% slower
        "no_regressions": report["summary"]["performance_regressions"] == 0,
    }

    ready_for_migration = all(criteria.values())

    return {
        "ready_for_migration": ready_for_migration,
        "criteria": criteria,
        "report": report,
        "recommendation": (
            "System is ready for migration to database views"
            if ready_for_migration
            else "System needs more testing before migration"
        ),
    }
