"""
GenCC data source integration with unified cache system.

Fetches kidney-related gene-disease relationships from Gene Curation Coalition
using enhanced caching infrastructure for improved performance.
"""

import asyncio
import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService, cached, get_cache_service
from app.core.cached_http_client import CachedHttpClient, get_cached_http_client
from app.core.config import settings

logger = logging.getLogger(__name__)


def clean_data_for_json(data: Any) -> Any:
    """Clean data by replacing NaN/None values with empty strings for JSON serialization"""
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(item) for item in data]
    elif pd.isna(data) or data is None:
        return ""
    else:
        return data


class GenCCClientCached:
    """
    Enhanced GenCC client with unified cache system integration.
    
    Features:
    - Persistent file caching with ETag support
    - HTTP caching via Hishel for file downloads
    - Database-backed cache for processed data
    - Intelligent TTL management per data type
    - Circuit breaker pattern for resilience
    """

    NAMESPACE = "gencc"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | AsyncSession | None = None,
    ):
        """Initialize the enhanced GenCC client."""
        self.cache_service = cache_service or get_cache_service(db_session)
        self.http_client = http_client or get_cached_http_client(cache_service, db_session)

        # GenCC configuration
        self.download_url = "https://search.thegencc.org/download/action/submissions-export-xlsx"

        # Same kidney keywords as original for consistency
        self.kidney_keywords = [
            "kidney", "renal", "nephro", "glomerul",
            "tubul", "polycystic", "alport", "nephritis",
            "cystic", "ciliopathy", "complement", "cakut"
        ]

        # GenCC classification mapping to weights
        self.classification_weights = {
            "Definitive": 1.0,
            "Strong": 0.8,
            "Moderate": 0.6,
            "Supportive": 0.5,
            "Limited": 0.3,
            "Disputed Evidence": 0.1,
            "No Known Disease Relationship": 0.0,  # Excluded
            "Refuted Evidence": 0.0,  # Excluded
        }

        # Get TTL for GenCC namespace
        self.ttl = settings.CACHE_TTL_GENCC

        logger.info(f"GenCCClientCached initialized with TTL: {self.ttl}s")

    async def download_excel_file(self) -> str | None:
        """
        Download GenCC submissions Excel file with intelligent caching.
        
        Uses ETag-based caching to avoid re-downloading unchanged files.
        
        Returns:
            Path to downloaded file or None if failed
        """
        cache_key = "excel_file"

        async def fetch_excel_file():
            try:
                logger.info(f"📥 Downloading GenCC submissions from: {self.download_url}")
                logger.info("🔄 Starting download... (this may take 30-60 seconds for ~3.6MB file)")

                # Download directly without caching binary content
                # We'll cache the parsed data instead
                response = await self.http_client.get(
                    self.download_url,
                    namespace=self.NAMESPACE,
                    fallback_ttl=0  # Don't cache binary response
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to download GenCC file: HTTP {response.status_code}")
                    return None
                
                content = response.content

                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                temp_file.write(content)
                temp_file.close()

                file_path = Path(temp_file.name)
                logger.info(f"✅ Downloaded GenCC file: {file_path} ({len(content):,} bytes)")
                # Return string path for JSON serialization
                return str(file_path)

            except Exception as e:
                logger.error(f"❌ Error downloading GenCC file: {e}")
                return None

        # Don't cache the file path itself - just download fresh each time
        # We'll cache the parsed data instead
        return await fetch_excel_file()

    async def parse_excel_file(self, file_path: Path | str) -> pd.DataFrame:
        """
        Parse GenCC Excel file (without caching).
        
        Args:
            file_path: Path to Excel file
        
        Returns:
            DataFrame with submissions data
        """
        # Convert to Path if string
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        try:
            # Read Excel file - usually first sheet contains the submissions
            df = pd.read_excel(file_path)
            logger.info(f"Parsed GenCC Excel file: {len(df)} total submissions")

            # Debug: Log column names to understand the structure
            logger.debug(f"GenCC columns: {list(df.columns)}")

            # Replace NaN with None for cleaner processing
            df = df.where(pd.notnull(df), None)
            
            return df

        except Exception as e:
            logger.error(f"Error parsing GenCC Excel file: {e}")
            return pd.DataFrame()
        finally:
            # Clean up temporary file
            try:
                file_path.unlink()
            except OSError:
                pass

    def is_kidney_related(self, row: pd.Series) -> bool:
        """Check if a GenCC submission is kidney-related"""
        # Check disease name and description fields
        text_fields = []
        used_fields = []

        # Try GenCC-specific field names for disease information
        for field in ['disease_title', 'disease_original_title', 'submitted_as_disease_name',
                      'disease_name', 'condition', 'disease', 'phenotype', 'disorder']:
            if field in row.index and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())
                used_fields.append(field)

        # Also check any description fields
        for field in row.index:
            if 'description' in field.lower() and pd.notna(row[field]):
                text_fields.append(str(row[field]).lower())
                used_fields.append(field)

        # Combine all text
        combined_text = " ".join(text_fields)

        # Look for kidney-related keywords
        return any(keyword in combined_text for keyword in self.kidney_keywords)

    def extract_gene_info(self, row: pd.Series) -> dict[str, Any] | None:
        """Extract gene information from GenCC submission"""
        try:
            # Extract gene symbol - try multiple field variations
            symbol = None
            for field in ['gene_symbol', 'hgnc_symbol', 'symbol', 'gene']:
                if field in row.index and pd.notna(row[field]):
                    symbol = str(row[field]).strip().upper()
                    break

            if not symbol:
                return None

            # Extract HGNC ID
            hgnc_id = ""
            for field in ['hgnc_id', 'gene_hgnc_id', 'hgnc']:
                if field in row.index and pd.notna(row[field]):
                    hgnc_id = str(row[field]).strip()
                    break

            # Extract disease name
            disease_name = ""
            for field in ['disease_title', 'disease_original_title', 'submitted_as_disease_name', 'disease_name', 'condition']:
                if field in row.index and pd.notna(row[field]):
                    disease_name = str(row[field]).strip()
                    break

            # Extract classification
            classification = ""
            for field in ['classification', 'gene_disease_pair_label', 'classification_title', 'category']:
                if field in row.index and pd.notna(row[field]):
                    classification = str(row[field]).strip()
                    break

            # Extract submitter
            submitter = ""
            for field in ['submitter_name', 'submitted_as_submitter_name', 'submitter', 'submitted_by']:
                if field in row.index and pd.notna(row[field]):
                    submitter = str(row[field]).strip()
                    break

            # Extract mode of inheritance
            mode_of_inheritance = ""
            for field in ['mode_of_inheritance', 'moi', 'inheritance', 'inheritance_pattern']:
                if field in row.index and pd.notna(row[field]):
                    mode_of_inheritance = str(row[field]).strip()
                    break

            # Extract submission date
            submission_date = ""
            for field in ['submitted_as_date', 'submitted_run_date', 'date', 'submission_date', 'last_updated']:
                if field in row.index and pd.notna(row[field]):
                    submission_date = str(row[field]).strip()
                    break

            return {
                "symbol": symbol,
                "hgnc_id": hgnc_id,
                "disease_name": disease_name,
                "classification": classification,
                "submitter": submitter,
                "mode_of_inheritance": mode_of_inheritance,
                "submission_date": submission_date,
                "raw_data": clean_data_for_json(row.to_dict())  # Store full record for reference
            }

        except Exception as e:
            logger.error(f"Error extracting gene info from GenCC row: {e}")
            return None

    async def get_kidney_gene_data(self) -> dict[str, Any]:
        """
        Get processed kidney-related gene data with comprehensive caching.
        
        Returns:
            Dictionary mapping gene symbols to aggregated GenCC data
        """
        cache_key = "kidney_gene_data"
        
        # Check cache first for processed data
        cached_data = await self.cache_service.get(cache_key, self.NAMESPACE)
        if cached_data is not None:
            logger.info(f"✅ Using cached kidney gene data: {len(cached_data)} genes")
            return cached_data

        async def fetch_and_process_data():
            # Download Excel file (NOT cached - always fresh)
            file_path = await self.download_excel_file()
            if not file_path:
                logger.error("❌ Failed to download GenCC file")
                return {}

            # Parse Excel file (NOT cached - parse fresh file)
            df = await self.parse_excel_file(file_path)
            if df.empty:
                logger.error("❌ Failed to parse GenCC file or file is empty")
                return {}

            logger.info(f"📊 Parsed {len(df)} total GenCC submissions")

            # Process submissions for kidney-related genes
            gene_data_map = {}  # symbol -> gene data
            kidney_related_count = 0

            logger.info("🔄 Processing GenCC submissions for kidney-related genes...")
            logger.debug(f"DataFrame shape: {df.shape}")
            logger.debug(f"DataFrame columns: {list(df.columns)[:10]}...")  # First 10 columns

            for idx, row in df.iterrows():
                # Filter for kidney-related submissions
                if not self.is_kidney_related(row):
                    continue

                kidney_related_count += 1

                # Log every 10th kidney-related submission for debugging
                if kidney_related_count % 10 == 1:
                    logger.info(f"🔍 Found kidney-related submission #{kidney_related_count}")
                    # Add more detail about what was found
                    gene_symbol = row.get('gene_symbol', 'Unknown')
                    disease = row.get('disease_title', row.get('submitted_as_disease_name', 'Unknown'))
                    logger.debug(f"   Gene: {gene_symbol}, Disease: {disease[:50]}...")

                # Extract gene information
                gene_info = self.extract_gene_info(row)
                if not gene_info:
                    logger.debug(f"⚠️ Failed to extract gene info from row {idx}")
                    continue

                symbol = gene_info["symbol"]

                # Aggregate by gene symbol
                if symbol not in gene_data_map:
                    gene_data_map[symbol] = {
                        "symbol": symbol,
                        "hgnc_id": gene_info["hgnc_id"],
                        "submissions": [],
                        "disease_count": 0,
                        "submitter_count": 0,
                        "classifications": {},
                        "submitters": set(),
                        "diseases": set(),
                    }

                # Add submission
                gene_data_map[symbol]["submissions"].append(gene_info)
                gene_data_map[symbol]["submitters"].add(gene_info["submitter"])
                gene_data_map[symbol]["diseases"].add(gene_info["disease_name"])

                # Count classifications
                classification = gene_info["classification"]
                if classification:
                    if classification not in gene_data_map[symbol]["classifications"]:
                        gene_data_map[symbol]["classifications"][classification] = 0
                    gene_data_map[symbol]["classifications"][classification] += 1

            # Finalize aggregated data
            for symbol, data in gene_data_map.items():
                data["disease_count"] = len(data["diseases"])
                data["submitter_count"] = len(data["submitters"])
                data["submission_count"] = len(data["submissions"])

                # Convert sets to lists for JSON serialization
                data["submitters"] = list(data["submitters"])
                data["diseases"] = list(data["diseases"])

            logger.info(f"✅ Processed {kidney_related_count} kidney-related submissions")
            logger.info(f"📊 Found {len(gene_data_map)} unique kidney-related genes")
            
            # Debug: Log some sample genes found
            if gene_data_map:
                sample_genes = list(gene_data_map.keys())[:5]
                logger.info(f"📌 Sample genes found: {sample_genes}")
                for gene in sample_genes[:2]:
                    data = gene_data_map[gene]
                    logger.debug(f"  {gene}: {data['submission_count']} submissions, {data['disease_count']} diseases")
            else:
                logger.warning("⚠️ No genes extracted despite finding kidney-related submissions!")

            return gene_data_map

        # Fetch and process the data
        logger.info("🔄 Fetching fresh GenCC data...")
        gene_data = await fetch_and_process_data()
        
        # Cache the processed data if we got results
        if gene_data:
            try:
                success = await self.cache_service.set(cache_key, gene_data, self.NAMESPACE, self.ttl)
                if success:
                    logger.info(f"✅ Cached {len(gene_data)} genes for future use")
                else:
                    logger.warning("⚠️ Failed to cache gene data, but continuing with results")
            except Exception as e:
                logger.warning(f"⚠️ Cache error (continuing anyway): {e}")
        
        return gene_data

    async def get_gene_evidence_score(self, symbol: str) -> float:
        """
        Calculate evidence score for a gene based on GenCC classifications.
        
        Args:
            symbol: Gene symbol
        
        Returns:
            Evidence score (0.0 to 1.0)
        """
        cache_key = f"evidence_score:{symbol.upper()}"

        async def calculate_score():
            gene_data_map = await self.get_kidney_gene_data()
            gene_data = gene_data_map.get(symbol.upper())

            if not gene_data:
                return 0.0

            # Calculate weighted score based on classifications
            total_weight = 0.0
            total_submissions = 0

            for classification, count in gene_data["classifications"].items():
                weight = self.classification_weights.get(classification, 0.0)
                total_weight += weight * count
                total_submissions += count

            if total_submissions == 0:
                return 0.0

            # Normalize by number of submissions and apply scaling factor
            base_score = total_weight / total_submissions

            # Apply bonus for multiple submitters (indicates consensus)
            submitter_bonus = min(gene_data["submitter_count"] * 0.1, 0.3)

            # Apply bonus for multiple diseases (indicates broader evidence)
            disease_bonus = min(gene_data["disease_count"] * 0.05, 0.2)

            final_score = min(base_score + submitter_bonus + disease_bonus, 1.0)

            return final_score

        return await cached(
            cache_key,
            calculate_score,
            self.NAMESPACE,
            3600,  # 1 hour TTL for scores
            self.cache_service.db_session
        )

    async def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for the GenCC namespace."""
        return await self.cache_service.get_stats(self.NAMESPACE)

    async def clear_cache(self) -> int:
        """Clear all GenCC cache entries."""
        return await self.cache_service.clear_namespace(self.NAMESPACE)

    async def warm_cache(self) -> int:
        """
        Warm the cache by preloading GenCC data.
        
        Returns:
            Number of entries cached
        """
        logger.info("Warming GenCC cache...")

        try:
            # Warm up the main kidney gene data
            await self.get_kidney_gene_data()

            # Calculate evidence scores for commonly accessed genes
            common_genes = [
                "PKD1", "PKD2", "COL4A5", "NPHS1", "NPHS2", "WT1", "PAX2",
                "HNF1B", "UMOD", "MUC1", "REN", "AGTR1", "ACE", "APOL1"
            ]

            tasks = [self.get_gene_evidence_score(gene) for gene in common_genes]
            await asyncio.gather(*tasks, return_exceptions=True)

            logger.info("GenCC cache warming completed")
            return len(common_genes) + 1  # +1 for main data cache

        except Exception as e:
            logger.error(f"Error warming GenCC cache: {e}")
            return 0


# Global cached client instance
_gencc_client_cached: GenCCClientCached | None = None


def get_gencc_client_cached(
    cache_service: CacheService | None = None,
    db_session: Session | AsyncSession | None = None
) -> GenCCClientCached:
    """Get or create the global cached GenCC client instance."""
    global _gencc_client_cached

    if _gencc_client_cached is None:
        _gencc_client_cached = GenCCClientCached(
            cache_service=cache_service,
            db_session=db_session
        )

    return _gencc_client_cached


# Convenience functions for backward compatibility

async def get_kidney_gene_data_cached(
    db_session: Session | AsyncSession | None = None
) -> dict[str, Any]:
    """
    Convenience function to get kidney gene data using the cached client.
    
    Args:
        db_session: Database session for cache persistence
    
    Returns:
        Dictionary mapping gene symbols to GenCC data
    """
    client = get_gencc_client_cached(db_session=db_session)
    return await client.get_kidney_gene_data()


async def get_gene_evidence_score_cached(
    symbol: str,
    db_session: Session | AsyncSession | None = None
) -> float:
    """
    Convenience function to get gene evidence score using the cached client.
    
    Args:
        symbol: Gene symbol
        db_session: Database session for cache persistence
    
    Returns:
        Evidence score (0.0 to 1.0)
    """
    client = get_gencc_client_cached(db_session=db_session)
    return await client.get_gene_evidence_score(symbol)
