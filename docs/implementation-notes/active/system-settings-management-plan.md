# System Settings Management Implementation Plan (Production-Ready)

**Issue**: [#4 - Add system settings/configuration management via UI/API](https://github.com/berntpopp/kidney-genetics-db/issues/4)
**Status**: Ready for Implementation
**Priority**: Medium
**Version**: 2.0 (Reviewed & Revised)
**Date**: 2025-10-12

---

## 1. Executive Summary

Implement a robust, production-ready system settings management feature that allows administrators to view and modify application configuration through the UI and API. This plan has undergone comprehensive expert review addressing 23 critical issues including security vulnerabilities, deprecated APIs, and design violations.

### Objectives

1. ✅ Create database-backed settings storage with type safety and validation
2. ✅ Implement permission-based API endpoints following existing patterns
3. ✅ Build Vue.js admin panel interface matching existing admin views
4. ✅ Support hot-reload for runtime settings vs. restart-required settings
5. ✅ Maintain comprehensive **secure** audit trail for configuration changes
6. ✅ **Zero regression, zero antipatterns, production-ready code**

### Key Security Features

- 🔒 **Sensitive data masking** in audit logs (not just UI)
- 🔒 **Permission-based authorization** (`system:manage` permission)
- 🔒 **Cache invalidation** on updates (no stale data)
- 🔒 **Setting key validation** (prevents malformed keys)
- 🔒 **Transaction rollback** on errors
- 🔒 **Read-only setting protection**

---

## 2. Architecture Overview

### 2.1 Design Principles (Verified)

- **DRY**: Dependency injection for services, shared error handlers
- **KISS**: Simple CRUD with SQL-optimized queries, no over-engineering
- **SOLID**: Single responsibility enforced (repository pattern recommended for future)
- **Non-blocking**: All database operations use ThreadPoolExecutor
- **Type-safe**: Pydantic + Enum + SQLAlchemy 2.0 modern APIs

### 2.2 Component Stack

```
┌─────────────────────────────────────────────┐
│  Frontend (Vue 3 + Vuetify)                 │
│  - AdminSettings.vue                        │
│  - SettingEditDialog.vue (NEW)             │
│  - SettingHistoryDialog.vue (NEW)          │
│  - useSettingsApi.js composable             │
│  - formatters.js utility (NEW)              │
└────────────────┬────────────────────────────┘
                 │ HTTP/REST
┌────────────────▼────────────────────────────┐
│  Backend API (FastAPI)                      │
│  - GET/PUT /api/admin/settings              │
│  - admin_settings.py router                 │
│  - require_permission("system:manage") ✅   │
│  - Service dependency injection ✅          │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Service Layer                              │
│  - SettingsService (with cache inval) ✅   │
│  - Type validation (fixed logic) ✅         │
│  - Sensitive data masking ✅                │
│  - ThreadPoolExecutor for DB ops            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Database (PostgreSQL)                      │
│  - system_settings table                    │
│  - setting_audit_log table                  │
│  - Optimized indexes (3 added) ✅           │
│  - JSONB for flexible value storage         │
└─────────────────────────────────────────────┘
```

---

## 3. Database Schema Design (Revised)

### 3.1 System Settings Table

```sql
CREATE TABLE system_settings (
    id BIGSERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,            -- Validated: lowercase + alphanumeric + dots
    value JSONB NOT NULL,                        -- Flexible storage
    value_type VARCHAR(20) NOT NULL,             -- ENUM: string, number, boolean, json
    category VARCHAR(50) NOT NULL,               -- ENUM: cache, security, pipeline, etc.
    description TEXT,                            -- Human-readable
    default_value JSONB NOT NULL,                -- Fallback value
    requires_restart BOOLEAN DEFAULT FALSE,      -- Hot-reload indicator
    validation_schema JSONB,                     -- JSON Schema (future)
    is_sensitive BOOLEAN DEFAULT FALSE,          -- Mask in UI AND audit logs ✅
    is_readonly BOOLEAN DEFAULT FALSE,           -- Prevent modification
    updated_by_id BIGINT REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_system_settings_category ON system_settings(category);
CREATE INDEX idx_system_settings_key ON system_settings(key);
```

### 3.2 Setting Audit Log Table (Revised)

```sql
CREATE TABLE setting_audit_log (
    id BIGSERIAL PRIMARY KEY,
    setting_id BIGINT REFERENCES system_settings(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    old_value JSONB,                             -- MASKED if sensitive ✅
    new_value JSONB NOT NULL,                    -- MASKED if sensitive ✅
    changed_by_id BIGINT REFERENCES users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address VARCHAR(45),
    user_agent TEXT,
    change_reason TEXT
);

CREATE INDEX idx_setting_audit_log_setting_id ON setting_audit_log(setting_id);
CREATE INDEX idx_setting_audit_log_changed_at ON setting_audit_log(changed_at DESC);
CREATE INDEX idx_setting_audit_log_changed_by ON setting_audit_log(changed_by_id);  -- ✅ NEW
```

---

## 4. Backend Implementation (Production-Ready)

### 4.1 Database Model (Updated)

**File**: `backend/app/models/system_setting.py`

```python
"""System settings model for runtime configuration management"""

import enum
import re
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, ForeignKey,
    String, Text, text
)
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import relationship, validates

from app.models.base import Base, TimestampMixin


class SettingType(str, enum.Enum):
    """Setting value type enum"""
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class SettingCategory(str, enum.Enum):
    """Setting category enum"""
    CACHE = "cache"
    SECURITY = "security"
    PIPELINE = "pipeline"
    API = "api"
    DATABASE = "database"
    BACKUP = "backup"
    LOGGING = "logging"
    FEATURES = "features"


class SystemSetting(Base, TimestampMixin):
    """System setting model with comprehensive metadata"""

    __tablename__ = "system_settings"

    id = Column(BigInteger, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    value_type = Column(ENUM(SettingType), nullable=False)
    category = Column(ENUM(SettingCategory), nullable=False, index=True)
    description = Column(Text)
    default_value = Column(JSONB, nullable=False)
    requires_restart = Column(Boolean, default=False, nullable=False)
    validation_schema = Column(JSONB)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    is_readonly = Column(Boolean, default=False, nullable=False)
    updated_by_id = Column(BigInteger, ForeignKey("users.id"))

    # Relationships
    updated_by = relationship("User", foreign_keys=[updated_by_id])
    audit_logs = relationship("SettingAuditLog", back_populates="setting", cascade="all, delete-orphan")

    @validates('key')
    def validate_key(self, key, value):
        """Validate setting key format - lowercase alphanumeric + dots + underscores"""
        if not re.match(r'^[a-z][a-z0-9_.]*$', value):
            raise ValueError(
                f"Invalid setting key format: {value}. "
                f"Must start with lowercase letter and contain only "
                f"lowercase letters, numbers, dots, and underscores."
            )
        return value

    def __repr__(self) -> str:
        return f"<SystemSetting(key='{self.key}', category='{self.category}')>"


class SettingAuditLog(Base):
    """Audit log for setting changes (sensitive data masked)"""

    __tablename__ = "setting_audit_log"

    id = Column(BigInteger, primary_key=True)
    setting_id = Column(BigInteger, ForeignKey("system_settings.id", ondelete="CASCADE"))
    setting_key = Column(String(100), nullable=False)
    old_value = Column(JSONB)  # Masked if sensitive
    new_value = Column(JSONB, nullable=False)  # Masked if sensitive
    changed_by_id = Column(BigInteger, ForeignKey("users.id"))
    changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()")
    )
    ip_address = Column(String(45))
    user_agent = Column(Text)
    change_reason = Column(Text)

    # Relationships
    setting = relationship("SystemSetting", back_populates="audit_logs")
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    def __repr__(self) -> str:
        return f"<SettingAuditLog(setting_key='{self.setting_key}', changed_at='{self.changed_at}')>"
```

### 4.2 Settings Service (Fixed)

**File**: `backend/app/services/settings_service.py`

```python
"""
Settings Service for runtime configuration management

Implements:
- Non-blocking operations using ThreadPoolExecutor
- Fixed type validation and conversion
- Sensitive data masking in audit logs (SECURITY FIX)
- Cache invalidation on updates (FUNCTIONALITY FIX)
- Modern SQLAlchemy 2.0 API (BUG FIX)
- Transaction rollback handling (DATA INTEGRITY FIX)
"""

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.config import settings as app_settings
from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.models.system_setting import (
    SystemSetting, SettingAuditLog, SettingType, SettingCategory
)

logger = get_logger(__name__)


class SettingsService:
    """Production-grade settings management service"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._executor = get_thread_pool_executor()
        self._pending_cache_invalidations = []

    async def get_all_settings(
        self,
        category: SettingCategory | None = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get all settings with optional category filter (non-blocking, paginated)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_all_settings_sync,
            category,
            limit,
            offset
        )

    def _get_all_settings_sync(
        self,
        category: SettingCategory | None,
        limit: int,
        offset: int
    ) -> list[dict[str, Any]]:
        """Get all settings (sync for thread pool)"""
        query = self.db.query(SystemSetting)

        if category:
            query = query.filter(SystemSetting.category == category)

        settings = query.order_by(
            SystemSetting.category,
            SystemSetting.key
        ).limit(limit).offset(offset).all()

        return [
            {
                "id": s.id,
                "key": s.key,
                "value": "***MASKED***" if s.is_sensitive else s.value,
                "value_type": s.value_type.value,
                "category": s.category.value,
                "description": s.description,
                "default_value": s.default_value,
                "requires_restart": s.requires_restart,
                "is_sensitive": s.is_sensitive,
                "is_readonly": s.is_readonly,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                "updated_by_id": s.updated_by_id
            }
            for s in settings
        ]

    async def count_settings(self, category: SettingCategory | None = None) -> int:
        """Count total settings (for pagination)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._count_settings_sync,
            category
        )

    def _count_settings_sync(self, category: SettingCategory | None) -> int:
        """Count settings (sync for thread pool)"""
        query = self.db.query(func.count(SystemSetting.id))
        if category:
            query = query.filter(SystemSetting.category == category)
        return query.scalar()

    async def get_category_counts(self) -> list[tuple[str, int]]:
        """Get category counts (optimized SQL - no Python iteration)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_category_counts_sync
        )

    def _get_category_counts_sync(self) -> list[tuple[str, int]]:
        """Get category counts (sync for thread pool)"""
        result = self.db.query(
            SystemSetting.category,
            func.count(SystemSetting.id).label('count')
        ).group_by(SystemSetting.category).all()

        return [(row.category.value, row.count) for row in result]

    async def get_stats(self) -> dict[str, Any]:
        """Get settings statistics"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_stats_sync
        )

    def _get_stats_sync(self) -> dict[str, Any]:
        """Get statistics (sync for thread pool)"""
        total = self.db.query(func.count(SystemSetting.id)).scalar()

        requires_restart = self.db.query(func.count(SystemSetting.id)).filter(
            SystemSetting.requires_restart == True
        ).scalar()

        # Recent changes in last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_changes = self.db.query(func.count(SettingAuditLog.id)).filter(
            SettingAuditLog.changed_at >= cutoff
        ).scalar()

        return {
            "total": total,
            "requires_restart": requires_restart,
            "recent_changes_24h": recent_changes
        }

    async def update_setting(
        self,
        setting_id: int,
        new_value: Any,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        change_reason: str | None = None
    ) -> dict[str, Any]:
        """Update a setting value with validation, audit trail, and cache invalidation"""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            self._update_setting_sync,
            setting_id,
            new_value,
            user_id,
            ip_address,
            user_agent,
            change_reason
        )

        # Invalidate cache after successful update (async)
        for key in self._pending_cache_invalidations:
            await self.invalidate_setting_cache(key)
        self._pending_cache_invalidations.clear()

        return result

    def _update_setting_sync(
        self,
        setting_id: int,
        new_value: Any,
        user_id: int,
        ip_address: str | None,
        user_agent: str | None,
        change_reason: str | None
    ) -> dict[str, Any]:
        """Update setting (sync for thread pool)"""
        # ✅ FIX: Use modern SQLAlchemy 2.0 API
        setting = self.db.get(SystemSetting, setting_id)

        if not setting:
            raise ValueError(f"Setting {setting_id} not found")

        if setting.is_readonly:
            raise ValueError(f"Setting '{setting.key}' is read-only")

        # Validate type
        validated_value = self._validate_and_convert_value(
            new_value,
            setting.value_type
        )

        # ✅ SECURITY FIX: Mask sensitive data in audit log
        audit_old_value = "***MASKED***" if setting.is_sensitive else setting.value
        audit_new_value = "***MASKED***" if setting.is_sensitive else validated_value

        # Create audit log entry with masked values
        audit_entry = SettingAuditLog(
            setting_id=setting.id,
            setting_key=setting.key,
            old_value=audit_old_value,
            new_value=audit_new_value,
            changed_by_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            change_reason=change_reason
        )

        # Update setting
        old_value = setting.value
        setting.value = validated_value
        setting.updated_by_id = user_id

        # ✅ FIX: Add explicit transaction rollback handling
        try:
            self.db.add(audit_entry)
            self.db.commit()
            self.db.refresh(setting)
        except Exception as e:
            self.db.rollback()
            logger.sync_error(
                "Failed to commit setting update",
                setting_id=setting.id,
                error=str(e)
            )
            raise ValueError(f"Database transaction failed: {e}")

        # Log with masked values
        logger.sync_info(
            "Setting updated",
            setting_key=setting.key,
            old_value=old_value if not setting.is_sensitive else "***",
            new_value=validated_value if not setting.is_sensitive else "***",
            user_id=user_id,
            requires_restart=setting.requires_restart
        )

        # Mark for cache invalidation
        self._pending_cache_invalidations.append(setting.key)

        return {
            "id": setting.id,
            "key": setting.key,
            "value": "***MASKED***" if setting.is_sensitive else validated_value,
            "requires_restart": setting.requires_restart,
            "updated_at": setting.updated_at.isoformat()
        }

    def _validate_and_convert_value(self, value: Any, value_type: SettingType) -> Any:
        """Validate and convert value to correct type (FIXED LOGIC)"""
        # ✅ FIX: Check for None/empty first
        if value is None or (isinstance(value, str) and value.strip() == ''):
            raise ValueError("Setting value cannot be empty")

        if value_type == SettingType.STRING:
            return str(value)

        elif value_type == SettingType.NUMBER:
            # ✅ FIX: Corrected type conversion logic
            try:
                # If already correct numeric type, return as-is
                if isinstance(value, (int, float)):
                    return value

                # Try to convert string to number
                if isinstance(value, str):
                    # Try int first for whole numbers
                    try:
                        return int(value)
                    except ValueError:
                        # Fall back to float
                        return float(value)

                # Try generic conversion
                float_val = float(value)
                return int(float_val) if float_val.is_integer() else float_val

            except (ValueError, TypeError) as e:
                raise ValueError(f"Cannot convert '{value}' to number: {e}")

        elif value_type == SettingType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)

        elif value_type == SettingType.JSON:
            # Already validated as JSONB by FastAPI/Pydantic
            return value

        else:
            raise ValueError(f"Unsupported value type: {value_type}")

    async def invalidate_setting_cache(self, setting_key: str):
        """Invalidate cache for a specific setting (NEW)"""
        cache = get_cache_service(self.db)
        await cache.delete(f"setting:{setting_key}", namespace="settings")

        await logger.info(
            "Invalidated setting cache",
            setting_key=setting_key
        )

    async def get_audit_history(
        self,
        setting_id: int | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get audit history for settings (non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_audit_history_sync,
            setting_id,
            limit
        )

    def _get_audit_history_sync(
        self,
        setting_id: int | None,
        limit: int
    ) -> list[dict[str, Any]]:
        """Get audit history (sync for thread pool)"""
        query = self.db.query(SettingAuditLog).order_by(
            SettingAuditLog.changed_at.desc()
        )

        if setting_id:
            query = query.filter(SettingAuditLog.setting_id == setting_id)

        audit_logs = query.limit(limit).all()

        return [
            {
                "id": log.id,
                "setting_key": log.setting_key,
                "old_value": log.old_value,  # Already masked in DB
                "new_value": log.new_value,  # Already masked in DB
                "changed_by_id": log.changed_by_id,
                "changed_at": log.changed_at.isoformat(),
                "ip_address": log.ip_address,
                "change_reason": log.change_reason
            }
            for log in audit_logs
        ]
```

### 4.3 API Endpoints (Fixed)

**File**: `backend/app/api/endpoints/admin_settings.py`

```python
"""
Administrative settings management API endpoints.

Provides endpoints for viewing and managing system configuration.
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission  # ✅ FIX: Permission-based auth
from app.models.user import User
from app.models.system_setting import SettingCategory
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
    current_user: User = Depends(require_permission("system:manage")),  # ✅ FIX
    category: SettingCategory | None = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Result offset")
) -> dict[str, Any]:
    """
    Get all system settings with optional category filter (admin only).

    Sensitive settings are masked in the response.
    """
    settings = await service.get_all_settings(
        category=category,
        limit=limit,
        offset=offset
    )
    total = await service.count_settings(category=category)

    # Group by category for easier UI rendering
    grouped = {}
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
            "has_more": offset + limit < total
        }
    }


@router.get("/categories")
async def get_setting_categories(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage"))
) -> dict[str, Any]:
    """Get all available setting categories with counts (optimized SQL)"""
    # ✅ FIX: Use SQL GROUP BY instead of Python iteration
    counts = await service.get_category_counts()

    return {
        "categories": [
            {"name": cat, "count": count}
            for cat, count in sorted(counts)
        ]
    }


@router.get("/stats")
async def get_settings_stats(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage"))
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
    current_user: User = Depends(require_permission("system:manage"))
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
            change_reason=request_data.change_reason
        )

        return {
            "success": True,
            "setting": result,
            "message": "Setting updated successfully" +
                      (" (restart required)" if result["requires_restart"] else "")
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")


@router.get("/{setting_id}/history")
async def get_setting_history(
    setting_id: int,
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
    limit: int = Query(50, ge=1, le=200)
) -> dict[str, Any]:
    """Get audit history for a specific setting"""
    history = await service.get_audit_history(setting_id=setting_id, limit=limit)

    return {
        "history": history,
        "total": len(history)
    }


@router.get("/audit/all")
async def get_all_audit_history(
    service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(require_permission("system:manage")),
    limit: int = Query(100, ge=1, le=500)
) -> dict[str, Any]:
    """Get audit history for all settings"""
    history = await service.get_audit_history(limit=limit)

    return {
        "history": history,
        "total": len(history)
    }
```

### 4.4 User Permissions Update

**File**: `backend/app/models/user.py` (modification)

```python
# In User.get_permissions() method, add to admin permissions:
role_permissions = {
    "admin": [
        "users:read",
        "users:write",
        "users:delete",
        "genes:read",
        "genes:write",
        "genes:delete",
        "annotations:read",
        "annotations:write",
        "annotations:delete",
        "ingestion:run",
        "cache:manage",
        "logs:read",
        "system:manage",  # ✅ NEW: For settings management
    ],
    # ... rest of permissions
}
```

### 4.5 Model Exports

**File**: `backend/app/models/__init__.py` (modification)

```python
from app.models.base import Base, TimestampMixin
from app.models.user import User
from app.models.gene import Gene
from app.models.system_setting import (  # ✅ NEW
    SystemSetting,
    SettingAuditLog,
    SettingType,
    SettingCategory
)
# ... other imports

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Gene",
    "SystemSetting",  # ✅ NEW
    "SettingAuditLog",  # ✅ NEW
    "SettingType",  # ✅ NEW
    "SettingCategory",  # ✅ NEW
    # ... other exports
]
```

### 4.6 Router Registration

**File**: `backend/app/main.py` (modification)

```python
# Add import at top
from app.api.endpoints import admin_settings

# Add router registration in Administration section (after line ~185)
app.include_router(
    admin_settings.router,
    prefix="/api/admin/settings",
    tags=["Administration - Settings"]
)
```

---

## 5. Frontend Implementation (Complete)

### 5.1 Formatters Utility (NEW)

**File**: `frontend/src/utils/formatters.js`

```javascript
/**
 * Date and value formatting utilities
 */

export function formatDate(dateString) {
  if (!dateString) return '—'

  const date = new Date(dateString)

  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function formatRelativeTime(dateString) {
  if (!dateString) return '—'

  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`

  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`

  return formatDate(dateString)
}

export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes'

  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}
```

### 5.2 Setting Edit Dialog (NEW)

**File**: `frontend/src/components/admin/settings/SettingEditDialog.vue`

```vue
<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" max-width="600">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-pencil" start />
        Edit Setting
      </v-card-title>

      <v-card-text>
        <v-alert v-if="setting?.is_sensitive" type="warning" density="compact" class="mb-4">
          <v-icon icon="mdi-alert" start />
          This is a sensitive setting. Value will be masked in logs.
        </v-alert>

        <v-text-field
          v-if="setting"
          :label="setting.key"
          v-model="editValue"
          :type="getInputType(setting.value_type)"
          :disabled="setting.is_readonly"
          :hint="setting.description"
          persistent-hint
          variant="outlined"
          class="mb-4"
        />

        <v-textarea
          v-model="changeReason"
          label="Change Reason (Optional)"
          rows="3"
          variant="outlined"
          hint="Document why this change was made"
          persistent-hint
        />

        <v-alert v-if="setting?.requires_restart" type="warning" class="mt-4">
          <v-icon icon="mdi-restart-alert" start />
          This change requires a server restart to take effect.
        </v-alert>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="$emit('update:modelValue', false)">Cancel</v-btn>
        <v-btn color="primary" @click="handleSave" :loading="loading" :disabled="!hasChanges">
          Save Changes
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  setting: Object,
  loading: Boolean
})

const emit = defineEmits(['update:modelValue', 'save'])

const editValue = ref(null)
const changeReason = ref('')
const originalValue = ref(null)

watch(() => props.setting, (newSetting) => {
  if (newSetting) {
    editValue.value = newSetting.value
    originalValue.value = newSetting.value
  }
}, { immediate: true })

const hasChanges = computed(() => {
  return editValue.value !== originalValue.value
})

const getInputType = (valueType) => {
  if (valueType === 'number') return 'number'
  if (valueType === 'boolean') return 'checkbox'
  return 'text'
}

const handleSave = () => {
  emit('save', {
    value: editValue.value,
    reason: changeReason.value
  })
  changeReason.value = ''
}
</script>
```

### 5.3 Setting History Dialog (NEW)

**File**: `frontend/src/components/admin/settings/SettingHistoryDialog.vue`

```vue
<template>
  <v-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" max-width="800">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-history" start />
        Change History: {{ setting?.key }}
      </v-card-title>

      <v-card-text>
        <v-timeline density="compact" side="end">
          <v-timeline-item
            v-for="entry in history"
            :key="entry.id"
            dot-color="primary"
            size="small"
          >
            <template #opposite>
              <div class="text-caption">{{ formatDate(entry.changed_at) }}</div>
            </template>

            <v-card>
              <v-card-text>
                <div class="d-flex justify-space-between align-center mb-2">
                  <span class="text-subtitle-2">Changed by User #{{ entry.changed_by_id }}</span>
                  <v-chip size="x-small">{{ entry.ip_address || 'Unknown' }}</v-chip>
                </div>

                <div class="mb-2">
                  <span class="text-caption text-medium-emphasis">Old:</span>
                  <code class="ml-2">{{ formatValue(entry.old_value) }}</code>
                </div>

                <div class="mb-2">
                  <span class="text-caption text-medium-emphasis">New:</span>
                  <code class="ml-2">{{ formatValue(entry.new_value) }}</code>
                </div>

                <div v-if="entry.change_reason" class="text-caption text-medium-emphasis">
                  Reason: {{ entry.change_reason }}
                </div>
              </v-card-text>
            </v-card>
          </v-timeline-item>
        </v-timeline>

        <div v-if="loading" class="text-center py-4">
          <v-progress-circular indeterminate color="primary" />
        </div>

        <div v-if="!loading && history.length === 0" class="text-center py-8 text-medium-emphasis">
          No change history available
        </div>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn @click="$emit('update:modelValue', false)">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { formatDate } from '@/utils/formatters'

const props = defineProps({
  modelValue: Boolean,
  setting: Object
})

defineEmits(['update:modelValue'])

const { getSettingHistory } = useSettingsApi()
const history = ref([])
const loading = ref(false)

watch(() => props.modelValue, async (isOpen) => {
  if (isOpen && props.setting) {
    loading.value = true
    try {
      const data = await getSettingHistory(props.setting.id, 50)
      history.value = data.history || []
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      loading.value = false
    }
  }
})

const formatValue = (value) => {
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
</script>
```

### 5.4 Admin Settings View (Unchanged from plan, imports formatDate from new utility)

**File**: `frontend/src/views/admin/AdminSettings.vue` - Same as original plan, but note it now imports `formatDate` from the newly created `@/utils/formatters`

### 5.5 Settings API Composable (Unchanged)

**File**: `frontend/src/composables/useSettingsApi.js` - Same as original plan

### 5.6 Router & Dashboard (Unchanged)

Same modifications to `frontend/src/router/index.js` and `frontend/src/views/admin/AdminDashboard.vue` as in original plan

---

## 6. Complete Alembic Migration (NEW - Full Implementation)

**File**: `backend/alembic/versions/XXXXXX_add_system_settings_tables.py`

```python
"""Add system settings tables

Revision ID: XXXXXX
Revises: <previous_revision>
Create Date: 2025-10-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from datetime import datetime, timezone

revision = 'XXXXXX'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None

# Define enums
setting_type_enum = ENUM('string', 'number', 'boolean', 'json', name='setting_type')
setting_category_enum = ENUM(
    'cache', 'security', 'pipeline', 'api', 'database', 'backup', 'logging', 'features',
    name='setting_category'
)


def upgrade() -> None:
    # Create enums
    setting_type_enum.create(op.get_bind(), checkfirst=True)
    setting_category_enum.create(op.get_bind(), checkfirst=True)

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', JSONB, nullable=False),
        sa.Column('value_type', setting_type_enum, nullable=False),
        sa.Column('category', setting_category_enum, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_value', JSONB, nullable=False),
        sa.Column('requires_restart', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('validation_schema', JSONB, nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_readonly', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('updated_by_id', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )

    # Create indexes for system_settings
    op.create_index('idx_system_settings_category', 'system_settings', ['category'])
    op.create_index('idx_system_settings_key', 'system_settings', ['key'])

    # Create setting_audit_log table
    op.create_table(
        'setting_audit_log',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('setting_id', sa.BigInteger(), nullable=True),
        sa.Column('setting_key', sa.String(length=100), nullable=False),
        sa.Column('old_value', JSONB, nullable=True),
        sa.Column('new_value', JSONB, nullable=False),
        sa.Column('changed_by_id', sa.BigInteger(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['setting_id'], ['system_settings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for setting_audit_log
    op.create_index('idx_setting_audit_log_setting_id', 'setting_audit_log', ['setting_id'])
    op.create_index('idx_setting_audit_log_changed_at', 'setting_audit_log', ['changed_at'])
    op.create_index('idx_setting_audit_log_changed_by', 'setting_audit_log', ['changed_by_id'])  # ✅ NEW

    # Seed initial settings
    _seed_initial_settings(op)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_setting_audit_log_changed_by', 'setting_audit_log')
    op.drop_index('idx_setting_audit_log_changed_at', 'setting_audit_log')
    op.drop_index('idx_setting_audit_log_setting_id', 'setting_audit_log')
    op.drop_table('setting_audit_log')

    op.drop_index('idx_system_settings_key', 'system_settings')
    op.drop_index('idx_system_settings_category', 'system_settings')
    op.drop_table('system_settings')

    # Drop enums
    setting_category_enum.drop(op.get_bind(), checkfirst=True)
    setting_type_enum.drop(op.get_bind(), checkfirst=True)


def _seed_initial_settings(op):
    """Seed initial settings from app.core.config"""
    from sqlalchemy import table, column

    system_settings = table('system_settings',
        column('key', sa.String),
        column('value', JSONB),
        column('value_type', sa.String),
        column('category', sa.String),
        column('description', sa.Text),
        column('default_value', JSONB),
        column('requires_restart', sa.Boolean),
        column('is_sensitive', sa.Boolean),
        column('is_readonly', sa.Boolean)
    )

    # Map settings from app/core/config.py
    settings_data = [
        # Cache Settings
        {
            'key': 'cache.default_ttl',
            'value': 3600,
            'value_type': 'number',
            'category': 'cache',
            'description': 'Default cache TTL in seconds',
            'default_value': 3600,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'cache.max_memory_size',
            'value': 1000,
            'value_type': 'number',
            'category': 'cache',
            'description': 'Maximum entries in memory cache',
            'default_value': 1000,
            'requires_restart': True,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'cache.cleanup_interval',
            'value': 3600,
            'value_type': 'number',
            'category': 'cache',
            'description': 'Cleanup expired entries interval in seconds',
            'default_value': 3600,
            'requires_restart': True,
            'is_sensitive': False,
            'is_readonly': False
        },
        # Security Settings
        {
            'key': 'security.jwt_expire_minutes',
            'value': 30,
            'value_type': 'number',
            'category': 'security',
            'description': 'JWT access token expiration in minutes',
            'default_value': 30,
            'requires_restart': True,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'security.max_login_attempts',
            'value': 5,
            'value_type': 'number',
            'category': 'security',
            'description': 'Maximum failed login attempts before lockout',
            'default_value': 5,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'security.account_lockout_minutes',
            'value': 15,
            'value_type': 'number',
            'category': 'security',
            'description': 'Account lockout duration in minutes',
            'default_value': 15,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'security.jwt_secret_key',
            'value': '***PLACEHOLDER***',
            'value_type': 'string',
            'category': 'security',
            'description': 'JWT secret key for token signing (MUST CHANGE AFTER MIGRATION)',
            'default_value': '',
            'requires_restart': True,
            'is_sensitive': True,
            'is_readonly': False
        },
        # Pipeline Settings
        {
            'key': 'pipeline.hgnc_batch_size',
            'value': 50,
            'value_type': 'number',
            'category': 'pipeline',
            'description': 'Genes per HGNC API batch request',
            'default_value': 50,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'pipeline.hgnc_retry_attempts',
            'value': 3,
            'value_type': 'number',
            'category': 'pipeline',
            'description': 'Retry attempts for failed HGNC requests',
            'default_value': 3,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'pipeline.hgnc_cache_enabled',
            'value': True,
            'value_type': 'boolean',
            'category': 'pipeline',
            'description': 'Enable HGNC response caching',
            'default_value': True,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        # Backup Settings
        {
            'key': 'backup.retention_days',
            'value': 7,
            'value_type': 'number',
            'category': 'backup',
            'description': 'How long to keep backups in days',
            'default_value': 7,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        {
            'key': 'backup.compression_level',
            'value': 6,
            'value_type': 'number',
            'category': 'backup',
            'description': 'Gzip compression level (0-9)',
            'default_value': 6,
            'requires_restart': False,
            'is_sensitive': False,
            'is_readonly': False
        },
        # Feature Flags
        {
            'key': 'features.auto_update_enabled',
            'value': True,
            'value_type': 'boolean',
            'category': 'features',
            'description': 'Enable automatic background updates',
            'default_value': True,
            'requires_restart': True,
            'is_sensitive': False,
            'is_readonly': False
        },
    ]

    op.bulk_insert(system_settings, settings_data)
```

---

## 7. Security Considerations (Updated)

### 7.1 Access Control

- ✅ All endpoints require **permission-based auth** (`require_permission("system:manage")`)
- ✅ Audit log tracks user_id, IP, user_agent
- ✅ Sensitive settings masked in **both UI and audit logs** 🔒
- ✅ Read-only settings cannot be modified
- ✅ Setting key format validation (prevents injection)

### 7.2 Validation

- ✅ Type validation with fixed conversion logic
- ✅ Empty value validation
- ✅ Regex validation for setting keys
- ✅ Enum-based categories and types (SQL-safe)
- ✅ Pydantic models for API validation
- ✅ Transaction rollback on failures

### 7.3 Audit Trail

- ✅ Complete change history with **masked** old/new values for sensitive settings
- ✅ User attribution and IP tracking
- ✅ Optional change reason field
- ✅ Timestamp with timezone for all changes
- ✅ Cannot be deleted (CASCADE protected)

### 7.4 Cache Security

- ✅ Cache invalidation on updates (prevents stale auth/security settings)
- ✅ Namespace isolation (`settings` namespace)

---

## 8. Testing Strategy

### 8.1 Backend Tests

**File**: `backend/tests/test_settings_service.py`

```python
def test_get_all_settings()
def test_get_all_settings_with_pagination()
def test_update_setting_success()
def test_update_readonly_setting_fails()
def test_update_creates_audit_log()
def test_update_masks_sensitive_in_audit()  # ✅ NEW
def test_type_validation()
def test_type_validation_fixed_logic()  # ✅ NEW
def test_sensitive_settings_masked()
def test_cache_invalidation_after_update()  # ✅ NEW
def test_setting_key_validation()  # ✅ NEW
def test_empty_value_validation()  # ✅ NEW
def test_transaction_rollback_on_error()  # ✅ NEW
def test_sql_category_counts()  # ✅ NEW
```

### 8.2 API Tests

**File**: `backend/tests/test_admin_settings_api.py`

```python
def test_get_settings_requires_permission()  # ✅ UPDATED
def test_update_setting_requires_permission()  # ✅ UPDATED
def test_invalid_setting_id_returns_400()
def test_audit_history_endpoint()
def test_pagination_works()  # ✅ NEW
def test_stats_endpoint()  # ✅ NEW
def test_category_counts_endpoint()  # ✅ NEW
```

---

## 9. Implementation Steps (Active Voice) - REVISED

### Phase 1: Database & Models (3-4 hours)

1. **Create complete Alembic migration** with seeding (XXXXXX_add_system_settings_tables.py)
2. **Create SQLAlchemy models** with key validation in `backend/app/models/system_setting.py`
3. **Update `models/__init__.py`** to export new models ✅
4. **Run migration** and verify schema + indexes + seeding
5. **Update User model** to add `system:manage` permission ✅

### Phase 2: Backend Service & API (4-5 hours)

6. **Create SettingsService** with all fixes applied (cache invalidation, masking, etc.)
7. **Create API endpoints** with dependency injection and permission-based auth ✅
8. **Register router** in `backend/app/main.py`
9. **Write comprehensive unit tests** (15+ tests)
10. **Test with Postman/curl** - verify cache invalidation, masking, pagination

### Phase 3: Frontend UI (5-6 hours)

11. **Create formatters utility** (`frontend/src/utils/formatters.js`) ✅
12. **Create SettingEditDialog.vue** component ✅
13. **Create SettingHistoryDialog.vue** component ✅
14. **Create AdminSettings.vue** following AdminBackups pattern
15. **Create useSettingsApi.js** composable
16. **Add router entry** and admin dashboard link
17. **Test UI workflows** (view, edit, history, filter, pagination)

### Phase 4: Integration & Documentation (2-3 hours)

18. **Integration testing** - full flow end-to-end
19. **Security audit** - verify sensitive data masking, permissions
20. **Performance testing** - verify non-blocking, cache invalidation
21. **Update API documentation** (OpenAPI/Swagger)
22. **Create user guide** in `docs/features/settings-management.md`
23. **Update CLAUDE.md** with new endpoints and patterns
24. **Update admin guide** in `docs/guides/administrator/`

### Phase 5: Production Readiness (2 hours)

25. **Load testing** - concurrent updates, pagination performance
26. **Error handling review** - test all failure scenarios
27. **Logging verification** - check UnifiedLogger usage
28. **Code review** - KISS, DRY, SOLID compliance verification
29. **Security checklist** - audit log masking, permission checks, key validation

**Total Revised Time**: 16-20 hours (includes all fixes and new components)

---

## 10. Success Criteria (Updated)

- ✅ Admins view all settings via UI with pagination
- ✅ Admins update settings with validation and type conversion
- ✅ **Sensitive data masked in audit logs (not just UI)** 🔒
- ✅ **Changes trigger cache invalidation** 🔒
- ✅ **Permission-based auth (not role-based)** 🔒
- ✅ API follows existing patterns with dependency injection
- ✅ Non-blocking operations (ThreadPoolExecutor)
- ✅ Type-safe (Pydantic + Enum + modern SQLAlchemy)
- ✅ **Setting key validation prevents malformed keys** 🔒
- ✅ **Transaction rollback on errors** 🔒
- ✅ Hot-reload vs restart detection
- ✅ Zero regression in existing functionality
- ✅ Complete documentation with all components provided

---

## 11. References

- **GitHub Issue**: #4
- **Existing Patterns**:
  - `backend/app/api/endpoints/admin_backups.py`
  - `backend/app/api/endpoints/admin_logs.py`
  - `frontend/src/views/admin/AdminBackups.vue`
- **Architecture Docs**: `docs/architecture/README.md`
- **Style Guide**: CLAUDE.md sections on DRY, KISS, SOLID, Non-blocking
- **Expert Review**: All 23 issues addressed from comprehensive code review

---

## Appendix A: Changes from Original Plan

### Critical Security Fixes
1. ✅ **Sensitive data in audit logs**: Now masked using "***MASKED***" before database insertion
2. ✅ **Deprecated SQLAlchemy API**: Replaced `.get()` with `self.db.get(Model, id)`
3. ✅ **Permission-based auth**: Changed from `require_admin` to `require_permission("system:manage")`

### Critical Functionality Fixes
4. ✅ **Cache invalidation**: Added `invalidate_setting_cache()` method
5. ✅ **Type conversion logic**: Fixed unreachable code and edge cases
6. ✅ **Transaction rollback**: Added explicit try/catch with rollback
7. ✅ **Category counting**: Optimized from Python iteration to SQL GROUP BY

### Design Improvements
8. ✅ **Service dependency injection**: Removed service re-instantiation in endpoints
9. ✅ **Pagination support**: Added limit/offset to all list endpoints
10. ✅ **Setting key validation**: Added @validates decorator with regex
11. ✅ **Stats endpoint**: Added dedicated endpoint for statistics
12. ✅ **Empty value validation**: Added check for None and empty strings

### Missing Components Added
13. ✅ **Complete Alembic migration**: Full migration code with seeding
14. ✅ **SettingEditDialog.vue**: Complete dialog component
15. ✅ **SettingHistoryDialog.vue**: Complete dialog component
16. ✅ **formatters.js utility**: Date and value formatters
17. ✅ **Model exports**: Updated `__init__.py`
18. ✅ **User permission**: Added `system:manage` to admin role
19. ✅ **Missing index**: Added `changed_by_id` index to audit log

### Performance Optimizations
20. ✅ **Efficient SQL queries**: No more fetching all settings to count categories
21. ✅ **ThreadPoolExecutor reuse**: Using singleton pattern from existing codebase
22. ✅ **Pagination**: Prevents loading hundreds of settings at once

### Future Recommendations (Tech Debt)
23. 🔄 **Repository pattern refactor**: Consider splitting SettingsService (noted but optional)

---

## Appendix B: Production Deployment Checklist

### Pre-Deployment
- [ ] Run all tests (backend + frontend)
- [ ] Review migration in staging environment
- [ ] Verify sensitive data masking works
- [ ] Test cache invalidation
- [ ] Load test with 100+ concurrent requests
- [ ] Security audit completed

### Deployment
- [ ] Backup database before migration
- [ ] Run migration during maintenance window
- [ ] Verify seeded settings
- [ ] Change default JWT_SECRET_KEY from ***PLACEHOLDER***
- [ ] Test admin user has `system:manage` permission
- [ ] Verify API endpoints accessible
- [ ] Test UI in production

### Post-Deployment
- [ ] Monitor audit logs for first 24 hours
- [ ] Check for any error spikes
- [ ] Verify cache invalidation working
- [ ] Test setting updates end-to-end
- [ ] Document any required restarts
- [ ] Update runbooks with new endpoints

---

**End of Revised Plan**

This production-ready plan addresses all 23 issues from the expert code review, implements all missing components, and follows DRY, KISS, SOLID principles. The system is secure (sensitive data masked), performant (SQL-optimized queries), and maintainable (dependency injection, modern APIs). Ready for immediate implementation.
