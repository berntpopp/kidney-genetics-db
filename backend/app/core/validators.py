"""
Centralized validation for SQL-safe parameters.
Implements DRY principle for input validation across the application.
"""

from fastapi import HTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class SQLSafeValidator:
    """
    Validate SQL parameters to prevent injection attacks.

    Provides centralized whitelist-based validation for column names,
    sort orders, and other SQL parameters.
    """

    # Whitelisted columns per table - extend as needed
    SAFE_COLUMNS = {
        "system_logs": {
            "id",
            "user_id",
            "action",
            "details",
            "level",
            "endpoint",
            "method",
            "status_code",
            "response_time_ms",
            "ip_address",
            "user_agent",
            "created_at",
            "updated_at",
            "timestamp",
            "logger",
            "message",
            "request_id",
            "path",
            "duration_ms",
            "error_type",
            "context",
            "source",
        },
        "genes": {
            "id",
            "gene_id",
            "hgnc_id",
            "approved_symbol",
            "gene_symbol",
            "approved_name",
            "alias_symbols",
            "entrez_id",
            "ensembl_gene_id",
            "omim_id",
            "uniprot_ids",
            "ccds_ids",
            "locus_group",
            "locus_type",
            "location",
            "location_sortable",
            "total_score",
            "percentage_score",
            "classification",
            "source_count",
            "sources",
            "annotation_count",
            "annotation_sources",
            "created_at",
            "updated_at",
            "is_active",
        },
        "users": {
            "id",
            "email",
            "full_name",
            "is_active",
            "is_admin",
            "is_superuser",
            "created_at",
            "updated_at",
            "last_login",
        },
        "gene_evidence": {
            "id",
            "gene_id",
            "source_name",
            "evidence_data",
            "score",
            "created_at",
            "updated_at",
        },
        "gene_scores": {
            "id",
            "gene_id",
            "total_score",
            "percentage_score",
            "classification",
            "evidence_count",
            "source_count",
            "created_at",
            "updated_at",
        },
        "cache_entries": {
            "id",
            "cache_key",
            "namespace",
            "data",
            "expires_at",
            "created_at",
            "updated_at",
            "access_count",
            "last_accessed",
        },
    }

    # Safe sort orders
    SAFE_SORT_ORDERS = {"ASC", "DESC", "asc", "desc"}

    # Safe operators for filtering
    SAFE_OPERATORS = {"=", "!=", ">", "<", ">=", "<=", "LIKE", "ILIKE", "IN", "NOT IN"}

    @classmethod
    def validate_column(cls, column: str, table: str) -> str:
        """
        Validate column name against whitelist.

        Args:
            column: Column name to validate
            table: Table name for context

        Returns:
            Validated column name

        Raises:
            HTTPException: If column is not safe
        """
        safe_columns = cls.SAFE_COLUMNS.get(table, set())

        # Handle column with table prefix (e.g., "g.gene_symbol")
        if "." in column:
            _, column_name = column.split(".", 1)
        else:
            column_name = column

        if column_name not in safe_columns:
            logger.warning(
                f"Rejected unsafe column: {column}", table=table, attempted_column=column
            )
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column '{column_name}'. Allowed columns: {', '.join(sorted(safe_columns))}",
            )

        return column

    @classmethod
    def validate_columns(cls, columns: list[str], table: str) -> list[str]:
        """
        Validate multiple column names.

        Args:
            columns: List of column names to validate
            table: Table name for context

        Returns:
            List of validated column names

        Raises:
            HTTPException: If any column is not safe
        """
        return [cls.validate_column(col, table) for col in columns]

    @classmethod
    def validate_sort_order(cls, order: str) -> str:
        """
        Validate sort order.

        Args:
            order: Sort order (ASC/DESC)

        Returns:
            Validated sort order in uppercase

        Raises:
            HTTPException: If order is not valid
        """
        if order.upper() not in cls.SAFE_SORT_ORDERS:
            logger.warning(f"Rejected invalid sort order: {order}")
            raise HTTPException(
                status_code=400,
                detail=f"Sort order must be one of: {', '.join(cls.SAFE_SORT_ORDERS)}",
            )

        return order.upper()

    @classmethod
    def validate_limit(cls, limit: int, max_limit: int = 1000) -> int:
        """
        Validate and cap limit parameter.

        Args:
            limit: Requested limit
            max_limit: Maximum allowed limit

        Returns:
            Validated limit value

        Raises:
            HTTPException: If limit is invalid
        """
        if limit < 1:
            raise HTTPException(status_code=400, detail="Limit must be positive")

        if limit > max_limit:
            logger.info(f"Capping limit from {limit} to {max_limit}")
            return max_limit

        return limit

    @classmethod
    def validate_offset(cls, offset: int, max_offset: int = 100000) -> int:
        """
        Validate offset parameter.

        Args:
            offset: Requested offset
            max_offset: Maximum allowed offset

        Returns:
            Validated offset value

        Raises:
            HTTPException: If offset is invalid
        """
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")

        if offset > max_offset:
            raise HTTPException(status_code=400, detail=f"Offset too large. Maximum: {max_offset}")

        return offset

    @classmethod
    def validate_operator(cls, operator: str) -> str:
        """
        Validate SQL operator.

        Args:
            operator: SQL operator to validate

        Returns:
            Validated operator

        Raises:
            HTTPException: If operator is not safe
        """
        operator_upper = operator.upper()

        if operator_upper not in cls.SAFE_OPERATORS:
            logger.warning(f"Rejected unsafe operator: {operator}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operator. Allowed: {', '.join(cls.SAFE_OPERATORS)}",
            )

        return operator_upper

    @classmethod
    def validate_table_name(cls, table: str) -> str:
        """
        Validate table name.

        Args:
            table: Table name to validate

        Returns:
            Validated table name

        Raises:
            HTTPException: If table is not recognized
        """
        if table not in cls.SAFE_COLUMNS:
            logger.warning(f"Rejected unknown table: {table}")
            raise HTTPException(status_code=400, detail=f"Unknown table: {table}")

        return table

    @classmethod
    def sanitize_search_term(cls, term: str) -> str:
        """
        Sanitize search term for LIKE/ILIKE queries.

        Args:
            term: Search term to sanitize

        Returns:
            Sanitized search term
        """
        # Escape special characters for LIKE patterns
        sanitized = term.replace("\\", "\\\\")
        sanitized = sanitized.replace("%", "\\%")
        sanitized = sanitized.replace("_", "\\_")
        sanitized = sanitized.replace("[", "\\[")

        return sanitized

    @classmethod
    def build_safe_where_clause(
        cls, conditions: dict[str, any], table: str, operator: str = "="
    ) -> tuple[str, dict]:
        """
        Build a safe WHERE clause from conditions.

        Args:
            conditions: Dictionary of column -> value conditions
            table: Table name for validation
            operator: Operator to use (default "=")

        Returns:
            Tuple of (WHERE clause string, parameters dict)
        """
        if not conditions:
            return "1=1", {}

        validated_operator = cls.validate_operator(operator)
        where_parts = []
        params = {}

        for column, value in conditions.items():
            validated_column = cls.validate_column(column, table)
            param_name = f"param_{column.replace('.', '_')}"

            where_parts.append(f"{validated_column} {validated_operator} :{param_name}")
            params[param_name] = value

        where_clause = " AND ".join(where_parts)
        return where_clause, params

    @classmethod
    def build_safe_order_by(
        cls, sort_by: str | None, sort_order: str | None, table: str, default_sort: str = "id"
    ) -> str:
        """
        Build a safe ORDER BY clause.

        Args:
            sort_by: Column to sort by
            sort_order: Sort order (ASC/DESC)
            table: Table name for validation
            default_sort: Default column if none provided

        Returns:
            Safe ORDER BY clause
        """
        if not sort_by:
            sort_by = default_sort

        validated_column = cls.validate_column(sort_by, table)
        validated_order = cls.validate_sort_order(sort_order or "ASC")

        return f"ORDER BY {validated_column} {validated_order}"


class QueryParameterValidator:
    """
    Validate common query parameters for API endpoints.
    """

    @staticmethod
    def validate_pagination(
        skip: int = 0, limit: int = 100, max_limit: int = 1000
    ) -> tuple[int, int]:
        """
        Validate pagination parameters.

        Args:
            skip: Number of records to skip
            limit: Number of records to return
            max_limit: Maximum allowed limit

        Returns:
            Validated (skip, limit) tuple
        """
        validated_offset = SQLSafeValidator.validate_offset(skip)
        validated_limit = SQLSafeValidator.validate_limit(limit, max_limit)

        return validated_offset, validated_limit

    @staticmethod
    def validate_sort_params(
        sort_by: str | None, sort_order: str | None, table: str, default_sort: str = "id"
    ) -> tuple[str, str]:
        """
        Validate sorting parameters.

        Args:
            sort_by: Column to sort by
            sort_order: Sort order
            table: Table name for validation
            default_sort: Default sort column

        Returns:
            Validated (sort_by, sort_order) tuple
        """
        if not sort_by:
            sort_by = default_sort

        validated_column = SQLSafeValidator.validate_column(sort_by, table)
        validated_order = SQLSafeValidator.validate_sort_order(sort_order or "ASC")

        return validated_column, validated_order
