"""
API endpoints for data source progress monitoring
OPTIMIZED: Uses event-driven pub/sub pattern instead of database polling
"""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.datasource_config import (
    DATA_SOURCE_CONFIG,
    INTERNAL_PROCESS_CONFIG,
    get_auto_update_sources,
    get_internal_process_config,
)
from app.core.dependencies import require_admin
from app.core.events import EventTypes, event_bus
from app.core.exceptions import DataSourceError
from app.core.logging import get_logger
from app.core.responses import ResponseBuilder
from app.models.progress import DataSourceProgress, SourceStatus
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter()


# Store active WebSocket connections with event-driven updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # Subscribe to progress events on initialization
        self._setup_event_subscriptions()

    def _setup_event_subscriptions(self):
        """Setup subscriptions to event bus"""
        event_bus.subscribe(EventTypes.PROGRESS_UPDATE, self._handle_progress_update)
        event_bus.subscribe(EventTypes.TASK_STARTED, self._handle_task_started)
        event_bus.subscribe(EventTypes.TASK_COMPLETED, self._handle_task_completed)
        event_bus.subscribe(EventTypes.TASK_FAILED, self._handle_task_failed)

    async def _handle_progress_update(self, data: dict):
        """Handle progress updates from event bus - NO MORE POLLING!"""
        # Wrap single update in array for frontend compatibility
        data_array = [data] if isinstance(data, dict) else data
        await self.broadcast({"type": "progress_update", "data": data_array})

    async def _handle_task_started(self, data: dict):
        """Handle task started events"""
        await self.broadcast({"type": "task_started", "data": data})

    async def _handle_task_completed(self, data: dict):
        """Handle task completed events"""
        await self.broadcast({"type": "task_completed", "data": data})

    async def _handle_task_failed(self, data: dict):
        """Handle task failed events"""
        await self.broadcast({"type": "task_failed", "data": data})

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        await logger.info("WebSocket connected", total_connections=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.sync_info("WebSocket disconnected", total_connections=len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return  # No connections to broadcast to

        disconnected = []
        for connection in self.active_connections:
            try:
                # Check if connection is still open before sending
                if connection.client_state.value == 1:  # 1 = CONNECTED state
                    await connection.send_json(message)
                else:
                    # Connection already closed, mark for cleanup
                    disconnected.append(connection)
            except WebSocketDisconnect:
                # Client disconnected gracefully
                await logger.warning(
                    "Client disconnected during broadcast",
                    total_connections=len(self.active_connections) - 1
                )
                disconnected.append(connection)
            except RuntimeError as e:
                # WebSocket already closed or in invalid state
                if "websocket.send" in str(e).lower() or "websocket.close" in str(e).lower():
                    await logger.warning(
                        "Attempted to send to closed websocket",
                        message_type=message.get("type")
                    )
                else:
                    await logger.error("Unexpected runtime error in websocket broadcast", error=e)
                disconnected.append(connection)
            except Exception as e:
                # Unexpected error
                await logger.error(
                    "Unexpected error sending to websocket",
                    error=e,
                    error_type=type(e).__name__
                )
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

        if disconnected:
            await logger.info(
                "Cleaned up disconnected websockets",
                cleaned=len(disconnected),
                remaining=len(self.active_connections)
            )


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time progress updates

    OPTIMIZED: No more polling! Updates are pushed via event bus.
    Clients connect to this endpoint to receive live updates about
    data source processing progress through event-driven architecture.
    """
    await manager.connect(websocket)
    try:
        # Send initial status of all sources with same format as REST API
        all_progress = db.query(DataSourceProgress).all()

        # Use same logic as get_all_status to format data consistently
        automated_sources = get_auto_update_sources()
        all_configured_sources = list(DATA_SOURCE_CONFIG.keys())
        internal_processes = list(INTERNAL_PROCESS_CONFIG.keys())

        formatted_data = []
        for p in all_progress:
            # Skip obsolete entries
            if (
                p.source_name not in all_configured_sources
                and p.source_name not in internal_processes
            ):
                continue

            status_dict = p.to_dict()

            # Add same category and metadata as REST API
            if p.source_name in automated_sources:
                status_dict["category"] = "data_source"
            elif p.source_name in all_configured_sources:
                status_dict["category"] = "hybrid_source"
            elif p.source_name in internal_processes:
                status_dict["category"] = "internal_process"
                # Add proper display metadata for internal processes
                process_config = get_internal_process_config(p.source_name)
                if process_config:
                    status_dict["display_name"] = process_config["display_name"]
                    status_dict["description"] = process_config["description"]
                    status_dict["icon"] = process_config["icon"]
            else:
                status_dict["category"] = "other"
            formatted_data.append(status_dict)

        initial_status = {"type": "initial_status", "data": formatted_data}
        await websocket.send_json(initial_status)

        # NO MORE POLLING! Just keep connection alive
        # Updates will be pushed through event bus subscriptions
        while True:
            # Wait for client messages (ping/pong or commands)
            try:
                # Use receive_text with a timeout for keepalive
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0,  # 30 second timeout for keepalive
                )
            except asyncio.TimeoutError:
                # Send a ping to keep connection alive
                await websocket.send_json({"type": "ping"})
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await logger.error("WebSocket error", error=e)
        manager.disconnect(websocket)


@router.get("/status")
async def get_all_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get current status of all data sources

    Returns:
        List of status dictionaries for all data sources
    """
    all_progress = db.query(DataSourceProgress).all()

    # Get valid data sources from config - only include automated sources for pipeline
    automated_sources = get_auto_update_sources()
    # Also include hybrid sources that could be run manually
    all_configured_sources = list(DATA_SOURCE_CONFIG.keys())
    internal_processes = list(INTERNAL_PROCESS_CONFIG.keys())

    result = []
    for p in all_progress:
        # Skip obsolete entries that are no longer in any config
        if p.source_name not in all_configured_sources and p.source_name not in internal_processes:
            continue

        status_dict = p.to_dict()

        # Add category and enhanced metadata
        if p.source_name in automated_sources:
            status_dict["category"] = "data_source"
        elif p.source_name in all_configured_sources:
            # Hybrid sources like DiagnosticPanels and Literature
            status_dict["category"] = "hybrid_source"
        elif p.source_name in internal_processes:
            status_dict["category"] = "internal_process"
            # Add proper display metadata for internal processes
            process_config = get_internal_process_config(p.source_name)
            if process_config:
                status_dict["display_name"] = process_config["display_name"]
                status_dict["description"] = process_config["description"]
                status_dict["icon"] = process_config["icon"]
        else:
            status_dict["category"] = "other"
        result.append(status_dict)

    # Count only actual data sources (not internal processes)
    data_source_count = len(
        [r for r in result if r["category"] in ["data_source", "hybrid_source"]]
    )

    return ResponseBuilder.build_success_response(
        data=result,
        meta={
            "total_sources": data_source_count,  # Only count actual data sources
            "total_entries": len(result),  # Total entries including internal processes
        },
    )


@router.get("/status/{source_name}")
async def get_source_status(source_name: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get status of a specific data source

    Args:
        source_name: Name of the data source

    Returns:
        Status dictionary for the specified source
    """
    progress = db.query(DataSourceProgress).filter_by(source_name=source_name).first()

    if not progress:
        raise DataSourceError(source_name, "status_check", "Source not found")

    return ResponseBuilder.build_success_response(
        data=progress.to_dict(), meta={"source_name": source_name}
    )


@router.post("/trigger/{source_name}", dependencies=[Depends(require_admin)])
async def trigger_update(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger an update for a specific data source

    Args:
        source_name: Name of the data source to update

    Returns:
        Status message
    """
    await logger.info(
        "Admin action: Source triggered",
        user_id=current_user.id,
        username=current_user.username,
        source_name=source_name,
    )
    await logger.info("API trigger endpoint called", source_name=source_name)

    from app.core.background_tasks import task_manager

    await logger.debug("Imported task_manager", task_manager=str(task_manager))

    progress = db.query(DataSourceProgress).filter_by(source_name=source_name).first()
    await logger.debug("Found progress record", progress=bool(progress), source_name=source_name)

    if not progress:
        await logger.error("Source not found in database", source_name=source_name)
        raise DataSourceError(source_name, "status_check", "Source not found")

    if progress.status == SourceStatus.running:
        await logger.warning("Source already running", source_name=source_name)
        return ResponseBuilder.build_success_response(
            data={"status": "already_running", "message": f"{source_name} is already running"}
        )

    # Trigger the update in background
    await logger.info(
        "About to call task_manager.run_source",
        source_name=source_name,
        task_manager_type=str(type(task_manager)),
    )

    try:
        task = asyncio.create_task(task_manager.run_source(source_name))
        await logger.info(
            "Successfully created asyncio task", task_done=task.done(), source_name=source_name
        )
    except Exception as e:
        await logger.error("Exception creating task", error=e, source_name=source_name)
        raise

    await logger.info("Returning success response", source_name=source_name)
    return ResponseBuilder.build_success_response(
        data={"status": "triggered", "message": f"Update triggered for {source_name}"},
        meta={"source_name": source_name},
    )


@router.post("/pause/{source_name}", dependencies=[Depends(require_admin)])
async def pause_source(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Pause a running data source update

    Args:
        source_name: Name of the data source to pause

    Returns:
        Status message
    """
    await logger.info(
        "Admin action: Source paused",
        user_id=current_user.id,
        username=current_user.username,
        source_name=source_name,
    )

    progress = db.query(DataSourceProgress).filter_by(source_name=source_name).first()

    if not progress:
        raise DataSourceError(source_name, "status_check", "Source not found")

    if progress.status != SourceStatus.running:
        return ResponseBuilder.build_success_response(
            data={"status": "not_running", "message": f"{source_name} is not running"}
        )

    progress.status = SourceStatus.paused
    progress.current_operation = "Paused by user"
    db.commit()

    # Broadcast update - now in async context so this works
    await manager.broadcast(
        {"type": "status_change", "source": source_name, "data": progress.to_dict()}
    )

    return ResponseBuilder.build_success_response(
        data={"status": "paused", "message": f"{source_name} has been paused"}
    )


@router.post("/resume/{source_name}", dependencies=[Depends(require_admin)])
async def resume_source(
    source_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Resume a paused data source update

    Args:
        source_name: Name of the data source to resume

    Returns:
        Status message
    """
    await logger.info(
        "Admin action: Source resumed",
        user_id=current_user.id,
        username=current_user.username,
        source_name=source_name,
    )

    from app.core.background_tasks import task_manager

    progress = db.query(DataSourceProgress).filter_by(source_name=source_name).first()

    if not progress:
        raise DataSourceError(source_name, "status_check", "Source not found")

    if progress.status != SourceStatus.paused:
        return ResponseBuilder.build_success_response(
            data={"status": "not_paused", "message": f"{source_name} is not paused"}
        )

    # Resume the update in background - now properly in async context
    asyncio.create_task(task_manager.run_source(source_name, resume=True))

    return ResponseBuilder.build_success_response(
        data={"status": "resumed", "message": f"{source_name} has been resumed"}
    )


@router.get("/dashboard")
async def get_dashboard_data(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Get dashboard data with summary statistics

    Returns:
        Dashboard data including overall statistics and source statuses
    """
    all_progress = db.query(DataSourceProgress).all()

    # Calculate overall statistics
    total_sources = len(all_progress)
    running_sources = sum(1 for p in all_progress if p.status == SourceStatus.running)
    completed_sources = sum(1 for p in all_progress if p.status == SourceStatus.completed)
    failed_sources = sum(1 for p in all_progress if p.status == SourceStatus.failed)

    total_items_processed = sum(p.items_processed for p in all_progress)
    total_items_added = sum(p.items_added for p in all_progress)
    total_items_updated = sum(p.items_updated for p in all_progress)
    total_items_failed = sum(p.items_failed for p in all_progress)

    dashboard_data = {
        "summary": {
            "total_sources": total_sources,
            "running": running_sources,
            "completed": completed_sources,
            "failed": failed_sources,
            "total_items_processed": total_items_processed,
            "total_items_added": total_items_added,
            "total_items_updated": total_items_updated,
            "total_items_failed": total_items_failed,
        },
        "sources": [p.to_dict() for p in all_progress],
    }

    return ResponseBuilder.build_success_response(
        data=dashboard_data, meta={"last_update": datetime.utcnow().isoformat()}
    )


# Export the connection manager for use by background tasks
def get_connection_manager():
    return manager
