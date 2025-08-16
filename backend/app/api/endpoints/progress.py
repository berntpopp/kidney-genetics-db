"""
API endpoints for data source progress monitoring
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.progress import DataSourceProgress, SourceStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to websocket: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time progress updates
    
    Clients connect to this endpoint to receive live updates about
    data source processing progress.
    """
    await manager.connect(websocket)
    try:
        # Send initial status of all sources
        all_progress = db.query(DataSourceProgress).all()
        initial_status = {
            "type": "initial_status",
            "data": [p.to_dict() for p in all_progress]
        }
        await websocket.send_json(initial_status)
        
        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(1)  # Check for updates every second
            
            # Get all running sources
            running_sources = db.query(DataSourceProgress).filter(
                DataSourceProgress.status == SourceStatus.running
            ).all()
            
            if running_sources:
                update = {
                    "type": "progress_update",
                    "data": [p.to_dict() for p in running_sources]
                }
                await websocket.send_json(update)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/status")
def get_all_status(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Get current status of all data sources
    
    Returns:
        List of status dictionaries for all data sources
    """
    all_progress = db.query(DataSourceProgress).all()
    
    # Categorize sources
    data_sources = ["PubTator", "PanelApp", "HPO", "ClinGen", "GenCC", "OMIM", "Literature"]
    internal_processes = ["Evidence_Aggregation", "HGNC_Normalization"]
    
    result = []
    for p in all_progress:
        status_dict = p.to_dict()
        # Add category field
        if p.source_name in data_sources:
            status_dict["category"] = "data_source"
        elif p.source_name in internal_processes:
            status_dict["category"] = "internal_process"
        else:
            status_dict["category"] = "other"
        result.append(status_dict)
    
    return result


@router.get("/status/{source_name}")
def get_source_status(
    source_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get status of a specific data source
    
    Args:
        source_name: Name of the data source
        
    Returns:
        Status dictionary for the specified source
    """
    progress = db.query(DataSourceProgress).filter_by(
        source_name=source_name
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"Source {source_name} not found")
    
    return progress.to_dict()


@router.post("/trigger/{source_name}")
async def trigger_update(
    source_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Trigger an update for a specific data source
    
    Args:
        source_name: Name of the data source to update
        
    Returns:
        Status message
    """
    from app.core.background_tasks import task_manager
    
    progress = db.query(DataSourceProgress).filter_by(
        source_name=source_name
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"Source {source_name} not found")
    
    if progress.status == SourceStatus.running:
        return {"status": "already_running", "message": f"{source_name} is already running"}
    
    # Trigger the update in background
    asyncio.create_task(task_manager.run_source(source_name))
    
    return {"status": "triggered", "message": f"Update triggered for {source_name}"}


@router.post("/pause/{source_name}")
def pause_source(
    source_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Pause a running data source update
    
    Args:
        source_name: Name of the data source to pause
        
    Returns:
        Status message
    """
    progress = db.query(DataSourceProgress).filter_by(
        source_name=source_name
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"Source {source_name} not found")
    
    if progress.status != SourceStatus.running:
        return {"status": "not_running", "message": f"{source_name} is not running"}
    
    progress.status = SourceStatus.paused
    progress.current_operation = "Paused by user"
    db.commit()
    
    # Broadcast update
    asyncio.create_task(manager.broadcast({
        "type": "status_change",
        "source": source_name,
        "data": progress.to_dict()
    }))
    
    return {"status": "paused", "message": f"{source_name} has been paused"}


@router.post("/resume/{source_name}")
async def resume_source(
    source_name: str,
    db: Session = Depends(get_db)
) -> Dict[str, str]:
    """
    Resume a paused data source update
    
    Args:
        source_name: Name of the data source to resume
        
    Returns:
        Status message
    """
    from app.core.background_tasks import task_manager
    
    progress = db.query(DataSourceProgress).filter_by(
        source_name=source_name
    ).first()
    
    if not progress:
        raise HTTPException(status_code=404, detail=f"Source {source_name} not found")
    
    if progress.status != SourceStatus.paused:
        return {"status": "not_paused", "message": f"{source_name} is not paused"}
    
    # Resume the update in background
    asyncio.create_task(task_manager.run_source(source_name, resume=True))
    
    return {"status": "resumed", "message": f"{source_name} has been resumed"}


@router.get("/dashboard")
def get_dashboard_data(db: Session = Depends(get_db)) -> Dict[str, Any]:
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
    
    return {
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
        "last_update": datetime.utcnow().isoformat()
    }


# Export the connection manager for use by background tasks
def get_connection_manager():
    return manager