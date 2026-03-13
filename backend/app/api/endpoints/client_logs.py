"""Client-side log reporting endpoint."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limit import LIMIT_CLIENT_LOGS, limiter
from app.models.system_logs import SystemLog
from app.schemas.client_log import ClientLogCreate, ClientLogResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/client-logs", tags=["client-logs"])


def _get_client_ip(request: Request) -> str:
    """Get real client IP, respecting X-Forwarded-For behind reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("", response_model=ClientLogResponse, status_code=201)
@limiter.limit(LIMIT_CLIENT_LOGS)
async def report_client_log(
    request: Request,
    response: Response,
    log_entry: ClientLogCreate,
    db: Session = Depends(get_db),
) -> ClientLogResponse:
    """Accept a client-side log entry and store in system_logs."""
    client_ip = _get_client_ip(request)

    system_log = SystemLog(
        level=log_entry.level,
        logger="frontend",
        message=log_entry.message,
        context={
            "frontend_url": log_entry.url,
            "frontend_context": log_entry.context,
        },
        ip_address=client_ip,
        user_agent=log_entry.user_agent,
        error_type=log_entry.error_type,
        error_message=log_entry.error_message,
        stack_trace=log_entry.stack_trace,
    )

    await run_in_threadpool(lambda: _save_log(db, system_log))
    await logger.info(
        "Client log received",
        log_level=log_entry.level,
        ip=client_ip,
    )

    return ClientLogResponse()


def _save_log(db: Session, log: SystemLog) -> None:
    """Save log entry to database (sync, runs in thread pool)."""
    try:
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
        raise
