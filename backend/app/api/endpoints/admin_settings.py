"""
Administrative settings management API endpoints.

Provides endpoints for viewing and managing system configuration.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.models.system_setting import SettingCategory
from app.models.user import User
from app.services.settings_service import SettingsService

router = APIRouter()


# ✅ NEW: Dependency injection for service (DRY)
def get_settings_service(db: Session = Depends(get_db)) -> SettingsService:
    """Get settings service instance"""
    return SettingsService(db)


# Request/Response Models
class UpdateSettingRequest(BaseModel):
    """Request model for updating a setting"""

    value: Any = Field(..., description="New value for the setting")
    change_reason: str | None = Field(None, description="Optional reason for change")


@router.get("/")
async def get_all_settings(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
    category: SettingCategory | None = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> dict[str, Any]:
    """
    Get all system settings with optional category filter (admin only).

    Sensitive settings are masked in the response.
    """
    settings = await service.get_all_settings(category=category, limit=limit, offset=offset)
    total = await service.count_settings(category=category)

    # Group by category for easier UI rendering
    grouped: dict[str, list[dict[str, Any]]] = {}
    for setting in settings:
        cat = setting["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(setting)

    return {
        "settings": settings,
        "grouped": grouped,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        },
    }


@router.get("/categories")
async def get_setting_categories(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
) -> dict[str, Any]:
    """Get all available setting categories with counts (optimized SQL)"""
    # ✅ FIX: Use SQL GROUP BY instead of Python iteration
    counts = await service.get_category_counts()

    return {"categories": [{"name": cat, "count": count} for cat, count in sorted(counts)]}


@router.get("/stats")
async def get_settings_stats(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
) -> dict[str, Any]:
    """Get settings statistics"""
    stats = await service.get_stats()
    return stats


@router.put("/{setting_id}")
async def update_setting(
    setting_id: int,
    request_data: UpdateSettingRequest,
    request: Request,
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
) -> dict[str, Any]:
    """
    Update a system setting (admin only).

    Changes are logged in the audit trail with user info.
    Settings marked as 'requires_restart' will indicate a restart is needed.
    """
    try:
        result = await service.update_setting(
            setting_id=setting_id,
            new_value=request_data.value,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            change_reason=request_data.change_reason,
        )

        return {
            "success": True,
            "setting": result,
            "message": "Setting updated successfully"
            + (" (restart required)" if result["requires_restart"] else ""),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}") from e


@router.get("/{setting_id}/history")
async def get_setting_history(
    setting_id: int,
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get audit history for a specific setting"""
    history = await service.get_audit_history(setting_id=setting_id, limit=limit)

    return {"history": history, "total": len(history)}


@router.get("/audit/all")
async def get_all_audit_history(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
    limit: int = Query(100, ge=1, le=500),
) -> dict[str, Any]:
    """Get audit history for all settings"""
    history = await service.get_audit_history(limit=limit)

    return {"history": history, "total": len(history)}
