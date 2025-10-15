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
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.models.system_setting import (
    SettingAuditLog,
    SettingCategory,
    SettingType,
    SystemSetting,
)

logger = get_logger(__name__)


class SettingsService:
    """Production-grade settings management service"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._executor = get_thread_pool_executor()
        self._pending_cache_invalidations = []

    async def get_all_settings(
        self, category: SettingCategory | None = None, limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get all settings with optional category filter (non-blocking, paginated)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._get_all_settings_sync, category, limit, offset
        )

    def _get_all_settings_sync(
        self, category: SettingCategory | None, limit: int, offset: int
    ) -> list[dict[str, Any]]:
        """Get all settings (sync for thread pool)"""
        query = self.db.query(SystemSetting)

        if category:
            query = query.filter(SystemSetting.category == category)

        settings = (
            query.order_by(SystemSetting.category, SystemSetting.key)
            .limit(limit)
            .offset(offset)
            .all()
        )

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
                "updated_by_id": s.updated_by_id,
            }
            for s in settings
        ]

    async def count_settings(self, category: SettingCategory | None = None) -> int:
        """Count total settings (for pagination)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._count_settings_sync, category)

    def _count_settings_sync(self, category: SettingCategory | None) -> int:
        """Count settings (sync for thread pool)"""
        query = self.db.query(func.count(SystemSetting.id))
        if category:
            query = query.filter(SystemSetting.category == category)
        return query.scalar()

    async def get_category_counts(self) -> list[tuple[str, int]]:
        """Get category counts (optimized SQL - no Python iteration)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._get_category_counts_sync)

    def _get_category_counts_sync(self) -> list[tuple[str, int]]:
        """Get category counts (sync for thread pool)"""
        result = (
            self.db.query(SystemSetting.category, func.count(SystemSetting.id).label("count"))
            .group_by(SystemSetting.category)
            .all()
        )

        return [(row.category.value, row.count) for row in result]

    async def get_stats(self) -> dict[str, Any]:
        """Get settings statistics"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self._get_stats_sync)

    def _get_stats_sync(self) -> dict[str, Any]:
        """Get statistics (sync for thread pool)"""
        total = self.db.query(func.count(SystemSetting.id)).scalar()

        requires_restart = (
            self.db.query(func.count(SystemSetting.id))
            .filter(SystemSetting.requires_restart == True)  # noqa: E712
            .scalar()
        )

        # Recent changes in last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_changes = (
            self.db.query(func.count(SettingAuditLog.id))
            .filter(SettingAuditLog.changed_at >= cutoff)
            .scalar()
        )

        return {
            "total": total,
            "requires_restart": requires_restart,
            "recent_changes_24h": recent_changes,
        }

    async def update_setting(
        self,
        setting_id: int,
        new_value: Any,
        user_id: int,
        ip_address: str | None = None,
        user_agent: str | None = None,
        change_reason: str | None = None,
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
            change_reason,
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
        change_reason: str | None,
    ) -> dict[str, Any]:
        """Update setting (sync for thread pool)"""
        # ✅ FIX: Use modern SQLAlchemy 2.0 API
        setting = self.db.get(SystemSetting, setting_id)

        if not setting:
            raise ValueError(f"Setting {setting_id} not found")

        if setting.is_readonly:
            raise ValueError(f"Setting '{setting.key}' is read-only")

        # Validate type
        validated_value = self._validate_and_convert_value(new_value, setting.value_type)

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
            change_reason=change_reason,
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
                "Failed to commit setting update", setting_id=setting.id, error=str(e)
            )
            raise ValueError(f"Database transaction failed: {e}") from e

        # Log with masked values
        logger.sync_info(
            "Setting updated",
            setting_key=setting.key,
            old_value=old_value if not setting.is_sensitive else "***",
            new_value=validated_value if not setting.is_sensitive else "***",
            user_id=user_id,
            requires_restart=setting.requires_restart,
        )

        # Mark for cache invalidation
        self._pending_cache_invalidations.append(setting.key)

        return {
            "id": setting.id,
            "key": setting.key,
            "value": "***MASKED***" if setting.is_sensitive else validated_value,
            "requires_restart": setting.requires_restart,
            "updated_at": setting.updated_at.isoformat(),
        }

    def _validate_and_convert_value(self, value: Any, value_type: SettingType) -> Any:
        """Validate and convert value to correct type (FIXED LOGIC)"""
        # ✅ FIX: Check for None/empty first
        if value is None or (isinstance(value, str) and value.strip() == ""):
            raise ValueError("Setting value cannot be empty")

        if value_type == SettingType.STRING:
            return str(value)

        elif value_type == SettingType.NUMBER:
            # ✅ FIX: Corrected type conversion logic
            try:
                # If already correct numeric type, return as-is
                # Note: Using Python 3.10+ union syntax (project requires >=3.10)
                if isinstance(value, int | float):
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
                raise ValueError(f"Cannot convert '{value}' to number: {e}") from e

        elif value_type == SettingType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
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

        await logger.info("Invalidated setting cache", setting_key=setting_key)

    async def get_audit_history(
        self, setting_id: int | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get audit history for settings (non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, self._get_audit_history_sync, setting_id, limit
        )

    def _get_audit_history_sync(self, setting_id: int | None, limit: int) -> list[dict[str, Any]]:
        """Get audit history (sync for thread pool)"""
        query = self.db.query(SettingAuditLog).order_by(SettingAuditLog.changed_at.desc())

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
                "change_reason": log.change_reason,
            }
            for log in audit_logs
        ]
