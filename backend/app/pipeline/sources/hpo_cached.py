"""
HPO (Human Phenotype Ontology) data source integration with unified cache system.

Fetches kidney-related phenotypes and associated genes from HPO
using enhanced caching infrastructure for improved performance.
"""

import asyncio
import hashlib
import logging
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, cached, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.config import settings

logger = logging.getLogger(__name__)

# URLs for data files
PHENOTYPE_HPOA_URL = "http://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa"
OMIM_GENEMAP2_URL = "https://data.omim.org/downloads/Z-5l6R50RfuMa18pDNht-Q/genemap2.txt"  # Requires license


class HPOClientCached:
    """
    Enhanced HPO client with unified cache system integration.
    
    Features:
    - Persistent file caching with ETag support
    - HTTP caching via Hishel for file downloads
    - Database-backed cache for processed data
    - Intelligent TTL management per data type
    - Circuit breaker pattern for resilience
    """

    NAMESPACE = "hpo"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
    ):
        """Initialize the enhanced HPO client."""
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)

        # HPO configuration
        self.base_url = settings.HPO_API_URL

        # Common kidney-related HPO terms
        self.kidney_hpo_terms = [
            "HP:0000083",  # Renal insufficiency
            "HP:0000112",  # Nephropathy
            "HP:0000113",  # Polycystic kidney dysplasia
            "HP:0000096",  # Glomerulonephritis
            "HP:0000097",  # Glomerulosclerosis
            "HP:0000100",  # Nephrotic syndrome
            "HP:0000103",  # Polyuria
            "HP:0000107",  # Renal cyst
            "HP:0000108",  # Renal corticomedullary cysts
            "HP:0000110",  # Renal dysplasia
            "HP:0000114",  # Proximal tubulopathy
            "HP:0000121",  # Nephrocalcinosis
            "HP:0000123",  # Nephritis
            "HP:0000793",  # Membranoproliferative glomerulonephritis
            "HP:0001919",  # Acute kidney injury
            "HP:0003073",  # Hypoalbuminemia
            "HP:0003774",  # Stage 5 chronic kidney disease
            "HP:0012211",  # Abnormal renal physiology
            "HP:0012622",  # Chronic kidney disease
        ]

        # Get TTL for HPO namespace
        self.ttl = settings.CACHE_TTL_HPO

        logger.info(f"HPOClientCached initialized with TTL: {self.ttl}s")

    async def download_phenotype_hpoa(self) -> bytes | None:
        """
        Download HPO phenotype.hpoa file with intelligent caching.
        
        Uses ETag-based caching to avoid re-downloading unchanged files.
        
        Returns:
            File content as bytes or None if failed
        """
        cache_key = "phenotype_hpoa_file"

        async def fetch_hpoa_file():
            try:
                logger.info(f"Downloading {PHENOTYPE_HPOA_URL}")

                # Use cached HTTP client with file download support
                content = await self.http_client.download_file(
                    PHENOTYPE_HPOA_URL,
                    namespace=self.NAMESPACE,
                    cache_key=cache_key,
                    etag_check=True
                )

                logger.info(f"Downloaded phenotype.hpoa: {len(content):,} bytes")
                return content

            except Exception as e:
                logger.error(f"Error downloading phenotype.hpoa: {e}")
                return None

        return await cached(
            cache_key,
            fetch_hpoa_file,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def parse_phenotype_hpoa(self, content: bytes) -> pd.DataFrame:
        """
        Parse HPO phenotype.hpoa file with caching of parsed results.
        
        Args:
            content: File content as bytes
        
        Returns:
            DataFrame with phenotype data
        """
        # Create cache key based on content hash for data integrity
        content_hash = hashlib.md5(content).hexdigest()
        cache_key = f"parsed_hpoa:{content_hash}"

        async def parse_file():
            try:
                # Parse the tab-separated file
                import io
                df = pd.read_csv(
                    io.StringIO(content.decode('utf-8')),
                    sep='\t',
                    comment='#',
                    low_memory=False
                )

                logger.info(f"Parsed phenotype.hpoa: {len(df)} records")

                # Convert DataFrame to JSON-serializable format for caching
                return df.to_dict('records')

            except Exception as e:
                logger.error(f"Error parsing phenotype.hpoa: {e}")
                return []

        records = await cached(
            cache_key,
            parse_file,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

        # Convert back to DataFrame
        return pd.DataFrame(records) if records else pd.DataFrame()

    async def get_kidney_related_genes(self) -> dict[str, Any]:
        """
        Get kidney-related genes from HPO with comprehensive caching.
        
        Returns:
            Dictionary mapping gene symbols to HPO data
        """
        cache_key = "kidney_related_genes"

        async def fetch_and_process_data():
            # Download phenotype.hpoa file (cached)
            content = await self.download_phenotype_hpoa()
            if not content:
                logger.error("Failed to download phenotype.hpoa")
                return {}

            # Parse file (cached)
            df = await self.parse_phenotype_hpoa(content)
            if df.empty:
                logger.error("Failed to parse phenotype.hpoa or file is empty")
                return {}

            logger.info(f"Processing {len(df)} HPO records for kidney-related genes...")

            # Filter for kidney-related terms
            kidney_records = df[
                df['hpo_id'].isin(self.kidney_hpo_terms) |
                df['hpo_name'].str.contains('kidney|renal|nephro|glomerul', case=False, na=False)
            ]

            logger.info(f"Found {len(kidney_records)} kidney-related HPO records")

            # Group by gene symbol
            gene_data_map = {}

            for _, row in kidney_records.iterrows():
                gene_symbol = row.get('gene_symbol')
                if pd.isna(gene_symbol) or not gene_symbol:
                    continue

                gene_symbol = str(gene_symbol).strip().upper()

                if gene_symbol not in gene_data_map:
                    gene_data_map[gene_symbol] = {
                        "symbol": gene_symbol,
                        "hgnc_id": row.get('hgnc_id', ''),
                        "phenotypes": [],
                        "hpo_terms": set(),
                        "diseases": set(),
                        "inheritance_patterns": set(),
                        "record_count": 0
                    }

                # Add phenotype data
                phenotype_data = {
                    "hpo_id": row.get('hpo_id'),
                    "hpo_name": row.get('hpo_name'),
                    "disease_id": row.get('disease_id'),
                    "disease_name": row.get('disease_name'),
                    "frequency": row.get('frequency'),
                    "onset": row.get('onset'),
                    "inheritance": row.get('inheritance'),
                    "evidence": row.get('evidence')
                }

                gene_data_map[gene_symbol]["phenotypes"].append(phenotype_data)
                gene_data_map[gene_symbol]["hpo_terms"].add(row.get('hpo_id'))

                if row.get('disease_name'):
                    gene_data_map[gene_symbol]["diseases"].add(row.get('disease_name'))

                if row.get('inheritance'):
                    gene_data_map[gene_symbol]["inheritance_patterns"].add(row.get('inheritance'))

                gene_data_map[gene_symbol]["record_count"] += 1

            # Convert sets to lists for JSON serialization
            for gene_data in gene_data_map.values():
                gene_data["hpo_terms"] = list(gene_data["hpo_terms"])
                gene_data["diseases"] = list(gene_data["diseases"])
                gene_data["inheritance_patterns"] = list(gene_data["inheritance_patterns"])
                gene_data["phenotype_count"] = len(gene_data["phenotypes"])
                gene_data["unique_hpo_terms"] = len(gene_data["hpo_terms"])
                gene_data["unique_diseases"] = len(gene_data["diseases"])

            logger.info(f"Processed {len(gene_data_map)} unique kidney-related genes from HPO")

            return gene_data_map

        return await cached(
            cache_key,
            fetch_and_process_data,
            self.NAMESPACE,
            self.ttl,
            self.cache_service.db_session
        )

    async def get_gene_phenotypes(self, symbol: str) -> list[dict[str, Any]]:
        """
        Get phenotypes for a specific gene.
        
        Args:
            symbol: Gene symbol
        
        Returns:
            List of phenotype data for the gene
        """
        cache_key = f"gene_phenotypes:{symbol.upper()}"

        async def fetch_gene_phenotypes():
            gene_data_map = await self.get_kidney_related_genes()
            gene_data = gene_data_map.get(symbol.upper())

            return gene_data.get("phenotypes", []) if gene_data else []

        return await cached(
            cache_key,
            fetch_gene_phenotypes,
            self.NAMESPACE,
            3600,  # 1 hour TTL for individual gene data
            self.cache_service.db_session
        )

    async def get_hpo_term_genes(self, hpo_term: str) -> list[str]:
        """
        Get genes associated with a specific HPO term.
        
        Args:
            hpo_term: HPO term ID (e.g., "HP:0000083")
        
        Returns:
            List of gene symbols
        """
        cache_key = f"hpo_term_genes:{hpo_term}"

        async def fetch_term_genes():
            gene_data_map = await self.get_kidney_related_genes()

            genes = []
            for symbol, data in gene_data_map.items():
                if hpo_term in data.get("hpo_terms", []):
                    genes.append(symbol)

            return genes

        return await cached(
            cache_key,
            fetch_term_genes,
            self.NAMESPACE,
            3600,  # 1 hour TTL for term-specific data
            self.cache_service.db_session
        )

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for the HPO namespace."""
        return await self.cache_service.get_stats(self.NAMESPACE)

    async def clear_cache(self) -> int:
        """Clear all HPO cache entries."""
        return await self.cache_service.clear_namespace(self.NAMESPACE)

    async def warm_cache(self) -> int:
        """
        Warm the cache by preloading HPO data.
        
        Returns:
            Number of entries cached
        """
        logger.info("Warming HPO cache...")

        try:
            # Warm up the main kidney genes data
            await self.get_kidney_related_genes()

            # Warm up data for common kidney HPO terms
            common_terms = [
                "HP:0000083",  # Renal insufficiency
                "HP:0000112",  # Nephropathy
                "HP:0000100",  # Nephrotic syndrome
                "HP:0012622",  # Chronic kidney disease
            ]

            tasks = [self.get_hpo_term_genes(term) for term in common_terms]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Warm up data for common kidney genes
            common_genes = [
                "PKD1", "PKD2", "COL4A5", "NPHS1", "NPHS2", "WT1"
            ]

            tasks = [self.get_gene_phenotypes(gene) for gene in common_genes]
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("HPO cache warming completed")
            return len(common_terms) + len(common_genes) + 1  # +1 for main data cache

        except Exception as e:
            logger.error(f"Error warming HPO cache: {e}")
            return 0


# Global cached client instance
_hpo_client_cached: HPOClientCached | None = None


def get_hpo_client_cached(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> HPOClientCached:
    """Get or create the global cached HPO client instance."""
    global _hpo_client_cached

    if _hpo_client_cached is None:
        _hpo_client_cached = HPOClientCached(
            cache_service=cache_service,
            db_session=db_session
        )

    return _hpo_client_cached


# Convenience functions for backward compatibility

async def get_kidney_related_genes_cached(
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any]:
    """
    Convenience function to get kidney-related genes using the cached client.
    
    Args:
        db_session: Database session for cache persistence
    
    Returns:
        Dictionary mapping gene symbols to HPO data
    """
    client = get_hpo_client_cached(db_session=db_session)
    return await client.get_kidney_related_genes()


async def get_gene_phenotypes_cached(
    symbol: str,
    db_session: Session | AsyncSession | None = None
) -> list[dict[str, Any]]:
    """
    Convenience function to get gene phenotypes using the cached client.
    
    Args:
        symbol: Gene symbol
        db_session: Database session for cache persistence
    
    Returns:
        List of phenotype data for the gene
    """
    client = get_hpo_client_cached(db_session=db_session)
    return await client.get_gene_phenotypes(symbol)
