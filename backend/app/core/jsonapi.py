"""
JSON:API compliant pagination, filtering, and sorting for FastAPI + SQLAlchemy.
Optimized for PostgreSQL with proper ORM integration.
Following KISS, DRY, and modularization principles.
"""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, and_, or_
from sqlalchemy.sql import ColumnElement

T = TypeVar("T")


# JSON:API Pagination Dependencies
def get_jsonapi_params(
    page_number: int = Query(1, alias="page[number]", ge=1, description="Page number"),
    page_size: int = Query(20, alias="page[size]", ge=1, le=100, description="Items per page"),
) -> dict:
    """Get JSON:API pagination parameters."""
    return {
        "page_number": page_number,
        "page_size": page_size,
    }


# JSON:API Page Response
class JSONAPIPage(BaseModel, Generic[T]):
    """
    JSON:API compliant page response format.
    """
    data: list[dict[str, Any]]
    meta: dict[str, Any]
    links: dict[str, str]


# Reusable Filter Builder for SQLAlchemy
class JSONAPIFilter:
    """
    Reusable filter builder for JSON:API compliant filtering with SQLAlchemy.
    """

    def __init__(self, model: type):
        """Initialize with SQLAlchemy model."""
        self.model = model
        self.conditions = []

    def add_search(
        self,
        search: str | None,
        fields: list[str],
    ) -> "JSONAPIFilter":
        """Add search filter across multiple fields."""
        if search:
            search_conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    search_conditions.append(column.ilike(f"%{search}%"))
            if search_conditions:
                self.conditions.append(or_(*search_conditions))
        return self

    def add_range(
        self,
        field: str,
        min_value: Any | None = None,
        max_value: Any | None = None,
    ) -> "JSONAPIFilter":
        """Add range filter (min/max)."""
        if hasattr(self.model, field):
            column = getattr(self.model, field)
            if min_value is not None:
                self.conditions.append(column >= min_value)
            if max_value is not None:
                self.conditions.append(column <= max_value)
        return self

    def add_exact(
        self,
        field: str,
        value: Any | None,
    ) -> "JSONAPIFilter":
        """Add exact match filter."""
        if value is not None and hasattr(self.model, field):
            column = getattr(self.model, field)
            self.conditions.append(column == value)
        return self

    def add_in(
        self,
        field: str,
        values: list[Any] | None,
    ) -> "JSONAPIFilter":
        """Add IN filter."""
        if values and hasattr(self.model, field):
            column = getattr(self.model, field)
            self.conditions.append(column.in_(values))
        return self

    def add_custom(
        self,
        condition: ColumnElement,
    ) -> "JSONAPIFilter":
        """Add custom SQLAlchemy condition."""
        if condition is not None:
            self.conditions.append(condition)
        return self

    def apply(self, query: Select) -> Select:
        """Apply all filters to SQLAlchemy query."""
        if self.conditions:
            return query.where(and_(*self.conditions))
        return query


# Reusable Sorter for SQLAlchemy
class JSONAPISorter:
    """
    Reusable sorter for JSON:API compliant sorting with SQLAlchemy.
    """

    def __init__(self, model: type, sort_string: str | None = None):
        """Initialize with SQLAlchemy model and optional sort string."""
        self.model = model
        self.sort_clauses = []
        if sort_string:
            self.parse_sort_string(sort_string)

    def parse_sort_string(self, sort_string: str) -> "JSONAPISorter":
        """Parse JSON:API sort string."""
        for field in sort_string.split(","):
            field = field.strip()
            if field:
                if field.startswith("-"):
                    field_name = field[1:]
                    descending = True
                else:
                    field_name = field.lstrip("+")
                    descending = False

                # Check if field exists on model
                if hasattr(self.model, field_name):
                    column = getattr(self.model, field_name)
                    if descending:
                        self.sort_clauses.append(column.desc().nulls_last())
                    else:
                        self.sort_clauses.append(column.asc().nulls_first())
        return self

    def add_default(self, field: str, descending: bool = False) -> "JSONAPISorter":
        """Add default sorting if no sort specified."""
        if not self.sort_clauses and hasattr(self.model, field):
            column = getattr(self.model, field)
            if descending:
                self.sort_clauses.append(column.desc().nulls_last())
            else:
                self.sort_clauses.append(column.asc().nulls_first())
        return self

    def apply(self, query: Select) -> Select:
        """Apply sorting to SQLAlchemy query."""
        if self.sort_clauses:
            return query.order_by(*self.sort_clauses)
        return query


# Query parameter dependencies for common filters
def get_search_filter(
    search: str | None = Query(None, alias="filter[search]", description="Search term"),
) -> str | None:
    """Get search filter from query params."""
    return search


def get_range_filters(
    field_name: str,
    min_alias: str = None,
    max_alias: str = None,
    min_ge: float = None,
    max_le: float = None,
) -> Callable:
    """Factory for range filter dependencies."""
    min_alias = min_alias or f"filter[min_{field_name}]"
    max_alias = max_alias or f"filter[max_{field_name}]"

    def dependency(
        min_value: float | None = Query(None, alias=min_alias, ge=min_ge),
        max_value: float | None = Query(None, alias=max_alias, le=max_le),
    ) -> tuple[float | None, float | None]:
        return min_value, max_value

    return dependency


def get_sort_param(
    default: str | None = None,
) -> Callable:
    """Factory for sort parameter dependency."""
    def dependency(
        sort: str | None = Query(default, description="Sort fields (e.g., -score,name)"),
    ) -> str | None:
        return sort

    return dependency


# Decorator for JSON:API endpoints
def jsonapi_endpoint(
    resource_type: str,
    model: type,
    searchable_fields: list[str] | None = None,
):
    """
    Decorator to mark an endpoint as JSON:API compliant.
    Provides metadata for automatic documentation and validation.
    """
    def decorator(func):
        func.__jsonapi_metadata__ = {
            "resource_type": resource_type,
            "model": model,
            "searchable_fields": searchable_fields or [],
        }
        return func

    return decorator


# Helper to build JSON:API response
def build_jsonapi_response(
    data: list[dict],
    total: int,
    page_number: int,
    page_size: int,
    base_url: str = "/api/resource",
) -> dict:
    """Build a JSON:API compliant response."""
    page_count = (total + page_size - 1) // page_size if total else 0

    # Build links
    links = {
        "self": f"{base_url}?page[number]={page_number}&page[size]={page_size}",
        "first": f"{base_url}?page[number]=1&page[size]={page_size}",
        "last": f"{base_url}?page[number]={page_count if page_count > 0 else 1}&page[size]={page_size}",
    }

    # Add prev/next links
    if page_number > 1:
        links["prev"] = f"{base_url}?page[number]={page_number - 1}&page[size]={page_size}"
    else:
        links["prev"] = None

    if page_number < page_count:
        links["next"] = f"{base_url}?page[number]={page_number + 1}&page[size]={page_size}"
    else:
        links["next"] = None

    return {
        "data": data,
        "meta": {
            "total": total,
            "page": page_number,
            "per_page": page_size,
            "page_count": page_count,
        },
        "links": links,
    }

