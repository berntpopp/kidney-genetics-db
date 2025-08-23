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

router = APIRouter(prefix="/api/admin/logs", tags=["admin", "logs"])


@router.get("/")
async def query_logs(
    db: Session = Depends(get_db),
    level: str | None = Query(None, description="Log level filter (INFO, WARNING, ERROR)"),
    source: str | None = Query(None, description="Source module filter"),
    request_id: str | None = Query(None, description="Request ID filter"),
    start_time: datetime | None = Query(None, description="Start time filter"),
    end_time: datetime | None = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset")
) -> dict[str, Any]:
    """
    Query system logs with filtering and pagination.
    
    Returns logs from the system_logs table with various filters.
    """
    try:
        # Build query
        query = "SELECT * FROM system_logs WHERE 1=1"
        params = {"limit": limit, "offset": offset}

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

        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"

        # Execute query
        result = db.execute(text(query), params)
        logs = []

        for row in result:
            logs.append({
                "id": row.id,
                "timestamp": row.timestamp.isoformat(),
                "level": row.level,
                "source": row.source,
                "message": row.message,
                "request_id": row.request_id,
                "user_id": row.user_id,
                "extra_data": row.extra_data
            })

        # Get total count
        count_query = "SELECT COUNT(*) FROM system_logs WHERE 1=1"
        count_params = {}

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
                "has_more": offset + limit < total_count
            }
        }

    except Exception:
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to query logs")


@router.get("/statistics")
async def get_log_statistics(
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze")
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
            {"cutoff": cutoff_time}
        ).fetchall()

        # Get top sources
        source_stats = db.execute(
            text("""
                SELECT source, COUNT(*) as count
                FROM system_logs
                WHERE timestamp >= :cutoff
                GROUP BY source
                ORDER BY count DESC
                LIMIT 10
            """),
            {"cutoff": cutoff_time}
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
            {"cutoff": cutoff_time}
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
                "hours": hours
            },
            "level_distribution": [
                {"level": row.level, "count": row.count}
                for row in level_stats
            ],
            "top_sources": [
                {"source": row.source, "count": row.count}
                for row in source_stats
            ],
            "error_timeline": [
                {
                    "hour": row.hour.isoformat(),
                    "errors": row.errors,
                    "total": row.total,
                    "error_rate": round(row.errors / row.total * 100, 2) if row.total > 0 else 0
                }
                for row in error_timeline
            ],
            "storage": {
                "table_size": size_estimate.table_size if size_estimate else "0 bytes",
                "total_rows": size_estimate.total_rows if size_estimate else 0
            }
        }

    except Exception:
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to generate statistics")


@router.delete("/cleanup")
async def cleanup_old_logs(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Delete logs older than this many days")
) -> dict[str, Any]:
    """
    Clean up old log entries to manage storage.
    
    Deletes log entries older than the specified number of days.
    """
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        # Count logs to be deleted
        count_result = db.execute(
            text("SELECT COUNT(*) FROM system_logs WHERE timestamp < :cutoff"),
            {"cutoff": cutoff_time}
        ).scalar()

        # Delete old logs
        db.execute(
            text("DELETE FROM system_logs WHERE timestamp < :cutoff"),
            {"cutoff": cutoff_time}
        )
        db.commit()

        # Logging removed to avoid circular import
        pass

        return {
            "success": True,
            "logs_deleted": count_result,
            "cutoff_date": cutoff_time.isoformat()
        }

    except Exception:
        db.rollback()
        # Logging removed to avoid circular import
        raise HTTPException(status_code=500, detail="Failed to cleanup logs")
