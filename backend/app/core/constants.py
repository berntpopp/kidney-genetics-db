"""Centralized constants for cache TTLs, timeouts, and limits.

All magic numbers for TTL/timeout values should be defined here.
"""

# Cache TTLs (seconds)
CACHE_TTL_SHORT = 300  # 5 minutes — semi-static metadata
CACHE_TTL_MEDIUM = 1800  # 30 minutes — moderate refresh
CACHE_TTL_LONG = 3600  # 1 hour — stable data (annotations, network)
CACHE_TTL_EXTENDED = 7200  # 2 hours — rarely changing data

# Backup timeouts (seconds)
BACKUP_TIMEOUT_STANDARD = 3600  # 1 hour — pg_dump
BACKUP_TIMEOUT_EXTENDED = 7200  # 2 hours — pg_restore

# Query limits
MAX_QUERY_RESULTS = 10000  # Server-enforced maximum for unbounded queries
NETWORK_BATCH_SIZE = 5000  # Chunked loading for network analysis
PIPELINE_CHUNK_SIZE = 1500  # Annotation pipeline batch size
