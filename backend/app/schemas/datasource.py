"""
Data source schemas
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DataSourceStats(BaseModel):
    """Statistics for a data source"""

    gene_count: int
    evidence_count: int
    last_updated: datetime | None
    metadata: dict[str, Any] | None = None


class DataSource(BaseModel):
    """Data source information"""

    name: str
    display_name: str
    description: str
    status: str  # active, inactive, error
    stats: DataSourceStats | None = None
    url: str | None = None
    documentation_url: str | None = None


class DataSourceList(BaseModel):
    """List of data sources"""

    sources: list[DataSource]
    total_active: int
    total_sources: int
    last_pipeline_run: datetime | None = None
    total_unique_genes: int | None = None
    total_evidence_records: int | None = None
    last_data_update: datetime | None = None
    explanations: dict[str, str] | None = None
