"""
Administrative log management API endpoints.

Provides endpoints for querying, managing, and analyzing system logs.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.validators import SQLSafeValidator
from app.models.user import User

router = APIRouter()


@router.get("/")
async def query_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    level: str | None = Query(None, description="Log level filter (INFO, WARNING, ERROR)"),
    source: str | None = Query(None, description="Source module filter"),
    request_id: str | None = Query(None, description="Request ID filter"),
    start_time: datetime | None = Query(None, description="Start time filter"),
    end_time: datetime | None = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
    sort_by: str = Query("timestamp", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
) -> dict[str, Any]:
    """
    Query system logs with filtering and pagination.

    Returns logs from the system_logs table with various filters.
    """
    try:
        # Build query
        query = "SELECT * FROM system_logs WHERE 1=1"
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if level:
            query += " AND level = :level"
            params["level"] = level.upper()

        if source:
            query += " AND source ILIKE :source"
            params["source"] = f"%{source}%"

        if request_id:
            query += " AND request_id = :request_id"
            params["request_id"] = request_id

        if start_time:
            query += " AND timestamp >= :start_time"
            params["start_time"] = start_time

        if end_time:
            query += " AND timestamp <= :end_time"
            params["end_time"] = end_time

        # Validate and apply sorting using centralized validator
        # Map common column names to actual database columns
        column_mapping = {
            "timestamp": "timestamp",
            "level": "level",
            "source": "logger",
            "logger": "logger",
            "message": "message",
            "request_id": "request_id",
            "user_id": "user_id",
            "ip_address": "ip_address",
            "path": "path",
            "method": "method",
            "status_code": "status_code",
            "duration_ms": "duration_ms",
            "error_type": "error_type",
            "created_at": "timestamp",  # Allow both names
        }

        # Map the sort_by field to actual column name
        actual_column = column_mapping.get(sort_by, "timestamp")

        # Validate column and sort order using centralized validator
        try:
            validated_column = SQLSafeValidator.validate_column(actual_column, "system_logs")
            validated_order = SQLSafeValidator.validate_sort_order(sort_order)
        except HTTPException:
            # Fall back to defaults if validation fails
            validated_column = "timestamp"
            validated_order = "DESC"

        query += f" ORDER BY {validated_column} {validated_order} LIMIT :limit OFFSET :offset"

        # Execute query
        result = db.execute(text(query), params)
        logs = []

        for row in result:
            # Extract request details from context
            context = row.context or {}
            log_entry = {
                "id": row.id,
                "timestamp": row.timestamp.isoformat(),
                "level": row.level,
                "source": row.logger,
                "message": row.message,
                "request_id": row.request_id,
                "user_id": row.user_id,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "path": row.path,
                "method": row.method,
                "status_code": row.status_code,
                "duration_ms": row.duration_ms,
                "error_type": row.error_type,
                "error_message": row.error_message,
                "stack_trace": row.stack_trace,
                "context": context,
                # Extract request details from context
                "request_body": context.get("request_body"),
                "query_params": context.get("query_params"),
                "headers": context.get("headers"),
                "client_info": context.get("client_info"),
            }
            logs.append(log_entry)

        # Get total count
        count_query = "SELECT COUNT(*) FROM system_logs WHERE 1=1"
        count_params: dict[str, Any] = {}

        if level:
            count_query += " AND level = :level"
            count_params["level"] = level.upper()
        if source:
            count_query += " AND source ILIKE :source"
            count_params["source"] = f"%{source}%"
        if request_id:
            count_query += " AND request_id = :request_id"
            count_params["request_id"] = request_id
        if start_time:
            count_query += " AND timestamp >= :start_time"
            count_params["start_time"] = start_time
        if end_time:
            count_query += " AND timestamp <= :end_time"
            count_params["end_time"] = end_time

        total_count = db.execute(text(count_query), count_params).scalar()

        # Logging removed to avoid circular import
        pass

        return {
            "logs": logs,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count,
            },
        }

    except Exception:
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to query logs") from None


@router.get("/statistics")
async def get_log_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
) -> dict[str, Any]:
    """
    Get log statistics for monitoring and analysis.

    Returns counts by level, top sources, error rates, etc.
    """
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get counts by level
        level_stats = db.execute(
            text("""
                SELECT level, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= :cutoff
                GROUP BY level
                ORDER BY count DESC
            """),
            {"cutoff": cutoff_time},
        ).fetchall()

        # Get top sources
        source_stats = db.execute(
            text("""
                SELECT logger as source, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= :cutoff
                GROUP BY logger
                ORDER BY count DESC
                LIMIT 10
            """),
            {"cutoff": cutoff_time},
        ).fetchall()

        # Get error rate over time (hourly)
        error_timeline = db.execute(
            text("""
                SELECT
                    DATE_TRUNC('hour', timestamp) as hour,
                    COUNT(*) FILTER (WHERE level = 'ERROR') as errors,
                    COUNT(*) as total
                FROM system_logs
                WHERE timestamp >= :cutoff
                GROUP BY hour
                ORDER BY hour DESC
            """),
            {"cutoff": cutoff_time},
        ).fetchall()

        # Get total size estimate
        size_estimate = db.execute(
            text("""
                SELECT
                    pg_size_pretty(pg_total_relation_size('system_logs')) as table_size,
                    COUNT(*) as total_rows
                FROM system_logs
            """)
        ).first()

        # Logging removed to avoid circular import
        pass

        return {
            "time_range": {
                "start": cutoff_time.isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "hours": hours,
            },
            "level_distribution": [{"level": row.level, "count": row.count} for row in level_stats],
            "top_sources": [{"source": row.source, "count": row.count} for row in source_stats],
            "error_timeline": [
                {
                    "hour": row.hour.isoformat(),
                    "errors": row.errors,
                    "total": row.total,
                    "error_rate": round(row.errors / row.total * 100, 2) if row.total > 0 else 0,
                }
                for row in error_timeline
            ],
            "storage": {
                "table_size": size_estimate.table_size if size_estimate else "0 bytes",
                "total_rows": size_estimate.total_rows if size_estimate else 0,
            },
        }

    except Exception:
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to generate statistics") from None


@router.delete("/cleanup")
async def cleanup_old_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
    days: int = Query(
        30, ge=0, le=365, description="Delete logs older than this many days (0 = all logs)"
    ),
) -> dict[str, Any]:
    """
    Clean up old log entries to manage storage.

    Deletes log entries older than the specified number of days.
    """
    try:
        if days == 0:
            # Delete all logs
            count_result = db.execute(text("SELECT COUNT(*) FROM system_logs")).scalar()
            db.execute(text("DELETE FROM system_logs"))
            cutoff_time = None
        else:
            # Delete logs older than specified days
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

            # Count logs to be deleted
            count_result = db.execute(
                text("SELECT COUNT(*) FROM system_logs WHERE timestamp < :cutoff"),
                {"cutoff": cutoff_time},
            ).scalar()

            # Delete old logs
            db.execute(
                text("DELETE FROM system_logs WHERE timestamp < :cutoff"), {"cutoff": cutoff_time}
            )

        db.commit()

        # Logging removed to avoid circular import
        pass

        return {
            "success": True,
            "logs_deleted": count_result,
            "cutoff_date": cutoff_time.isoformat() if cutoff_time else "All logs deleted",
        }

    except Exception:
        db.rollback()
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to cleanup logs") from None
