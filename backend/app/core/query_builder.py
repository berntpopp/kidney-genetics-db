"""
Query builder utilities for common database patterns.
OPTIMIZATION: Implements DRY principle for reusable query construction.
Enhanced to support complex operations including views, aggregations, and raw SQL.
"""

import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import or_, text
from sqlalchemy.orm import Query, Session

logger = logging.getLogger(__name__)

T = TypeVar("T")

class QueryBuilder(Generic[T]):
    """
    Enhanced reusable query builder for complex patterns.
    Implements DRY principle to avoid repetitive query construction.
    Supports views, aggregations, and raw SQL generation.
    """

    def __init__(self, session: Session, model: T):
        """
        Initialize query builder.

        Args:
            session: Database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model
        self.query = session.query(model)
        self._filters = []
        self._joins = []
        self._aggregations = []
        self._group_by = []
        self._raw_select = None
        self._view_name = None

    def search(self, search_term: str | None, *fields) -> "QueryBuilder[T]":
        """
        Add search filter across multiple fields.

        Args:
            search_term: Term to search for
            *fields: Field names to search in

        Returns:
            Self for method chaining
        """
        if search_term and fields:
            search_filter = f"%{search_term}%"
            conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    conditions.append(getattr(self.model, field).ilike(search_filter))
            if conditions:
                self.query = self.query.filter(or_(*conditions))
        return self

    def filter_by(self, **kwargs) -> "QueryBuilder[T]":
        """
        Add exact match filters.

        Args:
            **kwargs: Field=value pairs to filter by

        Returns:
            Self for method chaining
        """
        for field, value in kwargs.items():
            if value is not None and hasattr(self.model, field):
                self.query = self.query.filter(getattr(self.model, field) == value)
        return self

    def filter_range(
        self, field: str, min_value: Any | None = None, max_value: Any | None = None
    ) -> "QueryBuilder[T]":
        """
        Add range filter for a field.

        Args:
            field: Field name to filter
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)

        Returns:
            Self for method chaining
        """
        if hasattr(self.model, field):
            field_attr = getattr(self.model, field)
            if min_value is not None:
                self.query = self.query.filter(field_attr >= min_value)
            if max_value is not None:
                self.query = self.query.filter(field_attr <= max_value)
        return self

    def paginate(self, skip: int = 0, limit: int | None = 100) -> "QueryBuilder[T]":
        """
        Add pagination to query.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Self for method chaining
        """
        self.query = self.query.offset(skip)
        if limit:
            self.query = self.query.limit(limit)
        return self

    def sort(self, field: str, desc: bool = False) -> "QueryBuilder[T]":
        """
        Add sorting to query.

        Args:
            field: Field name to sort by
            desc: Sort in descending order if True

        Returns:
            Self for method chaining
        """
        if hasattr(self.model, field):
            order_field = getattr(self.model, field)
            if desc:
                self.query = self.query.order_by(order_field.desc())
            else:
                self.query = self.query.order_by(order_field)
        return self

    def filter_by_score(self, min_score: float) -> "QueryBuilder[T]":
        """
        Filter by minimum evidence score.

        Args:
            min_score: Minimum score threshold

        Returns:
            Self for method chaining
        """
        if hasattr(self.model, "evidence_score"):
            self.query = self.query.filter(self.model.evidence_score >= min_score)
        return self

    def join_related(self, *relationships) -> "QueryBuilder[T]":
        """
        Add joins for related tables.

        Args:
            *relationships: Relationship names to join

        Returns:
            Self for method chaining
        """
        for relationship in relationships:
            if hasattr(self.model, relationship):
                self.query = self.query.join(getattr(self.model, relationship))
        return self

    def join_view(self, view_name: str, on_clause: str) -> "QueryBuilder[T]":
        """
        Join with a database view.

        Args:
            view_name: Name of the view to join
            on_clause: SQL ON clause for the join

        Returns:
            Self for method chaining
        """
        self._view_name = view_name
        self._joins.append(("view", view_name, on_clause))
        return self

    def left_join(self, target, condition) -> "QueryBuilder[T]":
        """
        Add left outer join.

        Args:
            target: Target table/model to join
            condition: Join condition

        Returns:
            Self for method chaining
        """
        self.query = self.query.outerjoin(target, condition)
        self._joins.append(("left", target, condition))
        return self

    def aggregate(
        self, func_name: str, field: str, alias: str, distinct: bool = False
    ) -> "QueryBuilder[T]":
        """
        Add aggregation to query.

        Args:
            func_name: Aggregation function name (e.g., 'array_agg', 'count', 'sum')
            field: Field to aggregate
            alias: Alias for the aggregated result
            distinct: Whether to use DISTINCT in aggregation

        Returns:
            Self for method chaining
        """
        self._aggregations.append(
            {"func": func_name, "field": field, "alias": alias, "distinct": distinct}
        )
        return self

    def group_by(self, *fields) -> "QueryBuilder[T]":
        """
        Add GROUP BY clause.

        Args:
            *fields: Fields to group by

        Returns:
            Self for method chaining
        """
        for field in fields:
            if isinstance(field, str):
                if hasattr(self.model, field):
                    self._group_by.append(getattr(self.model, field))
                else:
                    # Handle raw field names (e.g., from views)
                    self._group_by.append(text(field))
            else:
                self._group_by.append(field)

        if self._group_by:
            self.query = self.query.group_by(*self._group_by)

        return self

    def build(self) -> Query:
        """
        Build and return the constructed query.

        Returns:
            Constructed SQLAlchemy query
        """
        return self.query

    def all(self) -> list:
        """
        Execute query and return all results.

        Returns:
            List of results
        """
        return self.query.all()

    def first(self) -> Any | None:
        """
        Execute query and return first result.

        Returns:
            First result or None
        """
        return self.query.first()

    def count(self) -> int:
        """
        Get count of matching records.

        Returns:
            Number of matching records
        """
        return self.query.count()

    def exists(self) -> bool:
        """
        Check if any matching records exist.

        Returns:
            True if records exist, False otherwise
        """
        return self.session.query(self.query.exists()).scalar()

    def build_raw_sql(self) -> tuple[str, dict]:
        """
        Build raw SQL string for complex queries with views and aggregations.

        Returns:
            Tuple of (SQL string, parameters dictionary)
        """
        if self._view_name and self._aggregations:
            # Build complex query with view join and aggregations
            return self._build_complex_sql()

        # Fall back to standard SQLAlchemy query compilation
        compiled = self.query.statement.compile(compile_kwargs={"literal_binds": True})
        return str(compiled), {}

    def _build_complex_sql(self) -> tuple[str, dict]:
        """
        Build complex SQL with view joins and aggregations.

        Returns:
            Tuple of (SQL string, parameters dictionary)
        """
        # Start with SELECT clause
        select_fields = []

        # Add regular fields from model
        table_name = self.model.__tablename__
        select_fields.extend(
            [
                f"{table_name}.id",
                f"{table_name}.approved_symbol",
                f"{table_name}.hgnc_id",
                f"{table_name}.aliases",
                f"{table_name}.created_at",
                f"{table_name}.updated_at",
            ]
        )

        # Add view fields if joined
        if self._view_name:
            select_fields.extend(
                [
                    f"{self._view_name}.source_count",
                    f"{self._view_name}.evidence_count",
                    f"{self._view_name}.raw_score",
                    f"{self._view_name}.percentage_score",
                    f"{self._view_name}.total_active_sources",
                ]
            )

        # Add aggregations
        for agg in self._aggregations:
            if agg["distinct"]:
                select_fields.append(f"{agg['func']}(DISTINCT {agg['field']}) as {agg['alias']}")
            else:
                select_fields.append(f"{agg['func']}({agg['field']}) as {agg['alias']}")

        sql = f"SELECT {', '.join(select_fields)}"

        # FROM clause
        sql += f" FROM {table_name}"

        # JOIN clauses
        for join_type, target, condition in self._joins:
            if join_type == "view":
                sql += f" JOIN {target} ON {condition}"
            elif join_type == "left":
                if hasattr(target, "__tablename__"):
                    target_name = target.__tablename__
                else:
                    target_name = str(target)
                sql += f" LEFT JOIN {target_name} ON {condition}"

        # WHERE clause
        params = {}

        # Add filters from the query
        # This is simplified - in production you'd need more sophisticated filter extraction

        # GROUP BY clause
        if self._group_by:
            group_fields = []
            for field in self._group_by:
                if hasattr(field, "key"):
                    group_fields.append(f"{table_name}.{field.key}")
                else:
                    group_fields.append(str(field))
            sql += f" GROUP BY {', '.join(group_fields)}"

        # ORDER BY and LIMIT would go here

        return sql, params

    def execute_aggregated(self) -> list[dict[str, Any]]:
        """
        Execute query with aggregations and return results as dictionaries.

        Returns:
            List of result dictionaries
        """
        if self._view_name or self._aggregations:
            # Execute as raw SQL for complex queries
            sql, params = self.build_raw_sql()
            result = self.session.execute(text(sql), params)

            # Convert to dictionaries
            columns = result.keys()
            return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

        # Standard query execution
        results = self.query.all()
        return [self._model_to_dict(r) for r in results]

    def _model_to_dict(self, model_instance) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            model_instance: SQLAlchemy model instance

        Returns:
            Dictionary representation
        """
        result = {}
        for column in model_instance.__table__.columns:
            result[column.name] = getattr(model_instance, column.name)
        return result

class QueryOptimizer:
    """
    Utilities for query optimization and analysis.
    """

    @staticmethod
    def explain_query(db: Session, query: Query) -> dict:
        """
        Get query execution plan for optimization.

        Args:
            db: Database session
            query: Query to analyze

        Returns:
            Execution plan details
        """
        try:
            # Compile query to SQL
            sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

            # Execute EXPLAIN ANALYZE
            result = db.execute(text(f"EXPLAIN ANALYZE {sql}"))

            # Parse execution plan
            plan_lines = [row[0] for row in result]

            # Extract key metrics
            execution_time = None
            planning_time = None

            for line in plan_lines:
                if "Execution Time:" in line:
                    execution_time = line.split(":")[1].strip()
                elif "Planning Time:" in line:
                    planning_time = line.split(":")[1].strip()

            return {
                "sql": sql,
                "plan": plan_lines,
                "execution_time": execution_time,
                "planning_time": planning_time,
            }

        except Exception as e:
            logger.error(f"Error explaining query: {e}")
            return {
                "error": str(e),
                "sql": str(query),
            }

    @staticmethod
    def add_query_hints(query: Query) -> Query:
        """
        Add optimizer hints for complex queries.

        Args:
            query: Query to optimize

        Returns:
            Optimized query
        """
        return query.execution_options(
            synchronize_session="fetch",
            populate_existing=True,
        )

    @staticmethod
    def suggest_indexes(db: Session, table_name: str) -> list[str]:
        """
        Suggest potential indexes based on query patterns.

        Args:
            db: Database session
            table_name: Table to analyze

        Returns:
            List of suggested index creation statements
        """
        suggestions = []

        # Check for missing indexes on foreign keys
        result = db.execute(
            text("""
            SELECT
                a.attname as column_name
            FROM pg_attribute a
            JOIN pg_class t ON a.attrelid = t.oid
            JOIN pg_namespace s ON t.relnamespace = s.oid
            WHERE t.relname = :table_name
                AND a.attnum > 0
                AND NOT a.attisdropped
                AND a.attname LIKE '%_id'
                AND NOT EXISTS (
                    SELECT 1 FROM pg_index i
                    WHERE i.indrelid = t.oid
                    AND a.attnum = ANY(i.indkey)
                )
        """),
            {"table_name": table_name},
        )

        for row in result:
            column = row[0]
            suggestions.append(f"CREATE INDEX idx_{table_name}_{column} ON {table_name}({column});")

        return suggestions

# Example usage functions
def get_genes_optimized(
    db: Session,
    search: str | None = None,
    min_score: float | None = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "approved_symbol",
    sort_desc: bool = False,
):
    """
    Example of using QueryBuilder for gene queries.

    Demonstrates DRY principle - reusable query construction.
    """
    from app.models.gene import Gene

    builder = QueryBuilder(db, Gene).search(search, "approved_symbol", "hgnc_id")
    if min_score:
        builder = builder.filter_by_score(min_score)
    return builder.paginate(skip, limit).sort(sort_by, sort_desc).all()

def analyze_slow_query(db: Session, query: Query) -> dict:
    """
    Analyze a slow query and provide optimization suggestions.
    """
    optimizer = QueryOptimizer()

    # Get execution plan
    plan = optimizer.explain_query(db, query)

    # Analyze for common issues
    suggestions = []

    if plan.get("plan"):
        plan_text = "\n".join(plan["plan"])

        # Check for sequential scans
        if "Seq Scan" in plan_text:
            suggestions.append("Query uses sequential scan - consider adding indexes")

        # Check for nested loops
        if "Nested Loop" in plan_text:
            suggestions.append("Query uses nested loops - may benefit from different join strategy")

        # Check execution time
        if plan.get("execution_time"):
            time_ms = float(plan["execution_time"].replace(" ms", ""))
            if time_ms > 100:
                suggestions.append(f"Query takes {time_ms}ms - consider optimization")

    return {
        "plan": plan,
        "suggestions": suggestions,
    }
