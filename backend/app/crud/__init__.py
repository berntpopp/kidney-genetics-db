"""
CRUD operations for the application.
"""

from .gene import gene_crud
from .gene_staging import log_crud, staging_crud

# For backwards compatibility with import style used in normalization
gene_staging = staging_crud

__all__ = ["gene_crud", "gene_staging", "staging_crud", "log_crud"]
