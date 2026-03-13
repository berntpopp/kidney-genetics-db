"""SQL safety utilities for dynamic DDL operations.

All dynamic SQL identifiers (view names, table names) MUST pass through
safe_identifier() before being interpolated into SQL strings.
"""

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

VALID_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def safe_identifier(name: str) -> str:
    """Validate and return a safe SQL identifier.

    Args:
        name: Identifier to validate (lowercase, underscores, max 63 chars).

    Returns:
        The validated identifier string.

    Raises:
        ValueError: If the identifier contains invalid characters or is too long.
    """
    if not VALID_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def refresh_materialized_view(session: Session, view_name: str, concurrent: bool = True) -> None:
    """Safely refresh a materialized view.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the materialized view to refresh.
        concurrent: Whether to use CONCURRENTLY clause.
    """
    name = safe_identifier(view_name)
    clause = "CONCURRENTLY " if concurrent else ""
    session.execute(text(f"REFRESH MATERIALIZED VIEW {clause}{name}"))
    session.commit()


def drop_materialized_view(session: Session, view_name: str) -> None:
    """Safely drop a materialized view.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the materialized view to drop.
    """
    name = safe_identifier(view_name)
    session.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE"))
    session.commit()


def get_view_definition(session: Session, view_name: str) -> str | None:
    """Safely get a view's SQL definition.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the view.

    Returns:
        View definition SQL or None if not found.
    """
    result: str | None = session.execute(
        text("SELECT pg_get_viewdef(:name::regclass, true)"),
        {"name": view_name},
    ).scalar()
    return result
