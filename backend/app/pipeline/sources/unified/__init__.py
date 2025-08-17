"""
Unified data source implementations.

This package contains the refactored, unified implementations of all data sources,
eliminating code duplication and providing consistent patterns for caching,
retrying, and error handling.
"""

from app.pipeline.sources.unified.base import UnifiedDataSource
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource

__all__ = [
    "UnifiedDataSource",
    "GenCCUnifiedSource",
    "PanelAppUnifiedSource",
    "PubTatorUnifiedSource",
    "HPOUnifiedSource",
    "ClinGenUnifiedSource",
    "get_unified_source",
]

# Source name to class mapping for factory function
SOURCE_MAP = {
    "GenCC": GenCCUnifiedSource,
    "PanelApp": PanelAppUnifiedSource,
    "PubTator": PubTatorUnifiedSource,
    "HPO": HPOUnifiedSource,
    "ClinGen": ClinGenUnifiedSource,
}


def get_unified_source(source_name: str, **kwargs) -> UnifiedDataSource:
    """
    Factory function to get appropriate unified data source client.

    Args:
        source_name: Name of the data source
        **kwargs: Additional arguments for client initialization

    Returns:
        Appropriate UnifiedDataSource instance

    Raises:
        ValueError: If source_name is not recognized
    """
    if source_name not in SOURCE_MAP:
        raise ValueError(f"Unknown data source: {source_name}")

    source_class = SOURCE_MAP[source_name]
    return source_class(**kwargs)
