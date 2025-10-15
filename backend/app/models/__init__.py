"""
Database models
"""

from app.models.backup_job import BackupJob, BackupStatus, BackupTrigger
from app.models.base import Base, TimestampMixin
from app.models.cache import CacheEntry
from app.models.data_release import DataRelease
from app.models.gene import Gene, GeneCuration, GeneEvidence, PipelineRun
from app.models.gene_annotation import AnnotationHistory, AnnotationSource, GeneAnnotation
from app.models.gene_staging import GeneNormalizationLog, GeneNormalizationStaging
from app.models.progress import DataSourceProgress, SourceStatus
from app.models.schema_version import SchemaVersion
from app.models.static_sources import StaticEvidenceUpload, StaticSource, StaticSourceAudit
from app.models.system_logs import SystemLog
from app.models.system_setting import SettingAuditLog, SettingCategory, SettingType, SystemSetting
from app.models.user import User

__all__ = [
    "AnnotationHistory",
    "AnnotationSource",
    "BackupJob",
    "BackupStatus",
    "BackupTrigger",
    "Base",
    "CacheEntry",
    "DataRelease",
    "DataSourceProgress",
    "Gene",
    "GeneAnnotation",
    "GeneCuration",
    "GeneEvidence",
    "GeneNormalizationLog",
    "GeneNormalizationStaging",
    "PipelineRun",
    "SchemaVersion",
    "SourceStatus",
    "StaticSource",
    "StaticSourceAudit",
    "StaticEvidenceUpload",
    "SystemLog",
    "SystemSetting",
    "SettingAuditLog",
    "SettingType",
    "SettingCategory",
    "TimestampMixin",
    "User",
]
