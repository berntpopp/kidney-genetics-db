"""
PubTator caching system for efficient data retrieval
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PubTatorCache:
    """Cache manager for PubTator search results"""
    
    def __init__(self, cache_dir: str = ".cache/pubtator"):
        """Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry_days = 7  # Cache valid for 7 days
        
    def _get_cache_key(self, query: str) -> str:
        """Generate cache key from query"""
        # Simple hash of query for filename
        import hashlib
        return hashlib.md5(query.encode()).hexdigest()
    
    def _get_cache_path(self, query: str) -> Path:
        """Get cache file path for query"""
        key = self._get_cache_key(query)
        return self.cache_dir / f"query_{key}.json"
    
    def _get_metadata_path(self, query: str) -> Path:
        """Get metadata file path for query"""
        key = self._get_cache_key(query)
        return self.cache_dir / f"meta_{key}.json"
    
    def is_cache_valid(self, query: str) -> bool:
        """Check if cache exists and is valid
        
        Args:
            query: Search query
            
        Returns:
            True if cache is valid
        """
        meta_path = self._get_metadata_path(query)
        
        if not meta_path.exists():
            return False
            
        try:
            with open(meta_path, 'r') as f:
                metadata = json.load(f)
            
            # Check if cache is expired
            cached_date = datetime.fromisoformat(metadata['cached_at'])
            expiry_date = cached_date + timedelta(days=self.cache_expiry_days)
            
            if datetime.now() > expiry_date:
                logger.info(f"Cache expired for query: {query[:50]}...")
                return False
                
            # Check if cache is complete
            if not metadata.get('complete', False):
                logger.info(f"Cache incomplete for query: {query[:50]}...")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def get_cached_data(self, query: str) -> dict[str, Any] | None:
        """Get cached data for query
        
        Args:
            query: Search query
            
        Returns:
            Cached data or None
        """
        if not self.is_cache_valid(query):
            return None
            
        cache_path = self._get_cache_path(query)
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            logger.info(f"Loaded cached data for query: {query[:50]}...")
            return data
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            return None
    
    def save_cache(self, query: str, data: dict[str, Any], complete: bool = False):
        """Save data to cache
        
        Args:
            query: Search query
            data: Data to cache
            complete: Whether the data is complete
        """
        cache_path = self._get_cache_path(query)
        meta_path = self._get_metadata_path(query)
        
        try:
            # Save data
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Save metadata
            metadata = {
                'query': query,
                'cached_at': datetime.now().isoformat(),
                'complete': complete,
                'total_genes': len(data),
            }
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Cached {len(data)} genes for query: {query[:50]}...")
            
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def clear_cache(self, query: str | None = None):
        """Clear cache files
        
        Args:
            query: Specific query to clear, or None to clear all
        """
        if query:
            cache_path = self._get_cache_path(query)
            meta_path = self._get_metadata_path(query)
            
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
                
            logger.info(f"Cleared cache for query: {query[:50]}...")
        else:
            # Clear all cache files
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
            logger.info("Cleared all PubTator cache")
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics
        
        Returns:
            Cache statistics
        """
        cache_files = list(self.cache_dir.glob("query_*.json"))
        meta_files = list(self.cache_dir.glob("meta_*.json"))
        
        total_size = sum(f.stat().st_size for f in cache_files)
        
        valid_caches = 0
        for meta_file in meta_files:
            try:
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                if metadata.get('complete', False):
                    valid_caches += 1
            except:
                pass
        
        return {
            'cache_dir': str(self.cache_dir),
            'total_queries_cached': len(cache_files),
            'valid_caches': valid_caches,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
        }