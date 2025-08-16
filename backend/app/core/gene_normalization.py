"""
Central gene normalization module using HGNC API

This module ensures all genes are properly normalized to HGNC standards
before entering the database. Unresolved genes go to a staging table
for manual review.
"""

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeneNormalizer:
    """Central gene normalization using HGNC API"""
    
    def __init__(self):
        """Initialize HGNC normalizer"""
        self.base_url = "https://rest.genenames.org"
        self.client = httpx.Client(
            timeout=30.0,
            headers={"Accept": "application/json"}
        )
        self.cache = {}  # In-memory cache for session
        
    def normalize_gene_symbol(self, 
                            gene_text: str, 
                            source_name: str,
                            original_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Normalize gene symbol using HGNC API with detailed logging
        
        Args:
            gene_text: Raw gene text from data source
            source_name: Name of data source (PubTator, ClinGen, etc.)
            original_data: Original data context for logging
            
        Returns:
            Dictionary with normalization results:
            {
                "success": bool,
                "approved_symbol": str | None,
                "hgnc_id": str | None,
                "aliases": list[str],
                "normalization_log": dict,
                "requires_manual_review": bool
            }
        """
        
        # Initialize result
        result = {
            "success": False,
            "approved_symbol": None,
            "hgnc_id": None,
            "aliases": [],
            "normalization_log": {
                "original_text": gene_text,
                "source": source_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "steps": [],
                "hgnc_api_called": False,
                "cache_hit": False
            },
            "requires_manual_review": False
        }
        
        if not gene_text:
            result["normalization_log"]["steps"].append("Empty gene text provided")
            result["requires_manual_review"] = True
            return result
            
        # Step 1: Basic text cleaning
        cleaned_text = self._clean_gene_text(gene_text)
        result["normalization_log"]["steps"].append(f"Cleaned text: '{gene_text}' -> '{cleaned_text}'")
        
        if not cleaned_text:
            result["normalization_log"]["steps"].append("Gene text became empty after cleaning")
            result["requires_manual_review"] = True
            return result
            
        # Step 2: Check cache first
        cache_key = cleaned_text.upper()
        if cache_key in self.cache:
            result["normalization_log"]["cache_hit"] = True
            result["normalization_log"]["steps"].append("Found in cache")
            cached_result = self.cache[cache_key]
            result.update(cached_result)
            return result
            
        # Step 3: Try HGNC API lookup
        hgnc_result = self._lookup_hgnc_api(cleaned_text)
        result["normalization_log"]["hgnc_api_called"] = True
        
        if hgnc_result["success"]:
            result["success"] = True
            result["approved_symbol"] = hgnc_result["symbol"]
            result["hgnc_id"] = hgnc_result["hgnc_id"]
            result["aliases"] = hgnc_result.get("aliases", [])
            result["normalization_log"]["steps"].append(
                f"HGNC API success: {hgnc_result['symbol']} ({hgnc_result['hgnc_id']})"
            )
            
            # Cache successful result
            cache_data = {
                "success": True,
                "approved_symbol": result["approved_symbol"],
                "hgnc_id": result["hgnc_id"],
                "aliases": result["aliases"]
            }
            self.cache[cache_key] = cache_data
            
        else:
            result["normalization_log"]["steps"].append(f"HGNC API failed: {hgnc_result['error']}")
            
            # Step 4: Try fuzzy matching strategies
            fuzzy_result = self._try_fuzzy_matching(cleaned_text)
            if fuzzy_result["success"]:
                result["success"] = True
                result["approved_symbol"] = fuzzy_result["symbol"]
                result["hgnc_id"] = fuzzy_result["hgnc_id"]
                result["aliases"] = fuzzy_result.get("aliases", [])
                result["normalization_log"]["steps"].append(
                    f"Fuzzy matching success: {fuzzy_result['symbol']} ({fuzzy_result['hgnc_id']})"
                )
                
                # Cache fuzzy result
                cache_data = {
                    "success": True,
                    "approved_symbol": result["approved_symbol"],
                    "hgnc_id": result["hgnc_id"],
                    "aliases": result["aliases"]
                }
                self.cache[cache_key] = cache_data
            else:
                result["normalization_log"]["steps"].append("Fuzzy matching failed")
                result["requires_manual_review"] = True
                
        return result
        
    def _clean_gene_text(self, gene_text: str) -> str:
        """Clean and standardize gene text"""
        if not gene_text:
            return ""
            
        # Convert to uppercase
        cleaned = gene_text.upper().strip()
        
        # Remove common prefixes/suffixes
        patterns_to_remove = [
            r'\bHUMAN\b',
            r'\bPROTEIN\b',
            r'\bGENE\b',
            r'\(.*?\)',  # Remove parentheses and content
            r'\[.*?\]',  # Remove brackets and content
        ]
        
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned)
            
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove trailing numbers/punctuation that aren't part of gene names
        cleaned = re.sub(r'[^\w\-]+$', '', cleaned)
        
        # Basic validation - gene symbols should start with letter
        if cleaned and not cleaned[0].isalpha():
            return ""
            
        return cleaned
        
    def _lookup_hgnc_api(self, gene_symbol: str) -> dict[str, Any]:
        """Lookup gene using HGNC REST API"""
        try:
            # Try exact symbol match first
            response = self.client.get(
                f"{self.base_url}/fetch/symbol/{gene_symbol}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    doc = data["response"]["docs"][0]
                    return {
                        "success": True,
                        "symbol": doc.get("symbol", ""),
                        "hgnc_id": doc.get("hgnc_id", ""),
                        "aliases": doc.get("alias_symbol", [])
                    }
                    
            # Try previous symbols/aliases
            response = self.client.get(
                f"{self.base_url}/fetch/prev_symbol/{gene_symbol}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    doc = data["response"]["docs"][0]
                    return {
                        "success": True,
                        "symbol": doc.get("symbol", ""),
                        "hgnc_id": doc.get("hgnc_id", ""),
                        "aliases": doc.get("alias_symbol", [])
                    }
                    
            # Try alias symbols
            response = self.client.get(
                f"{self.base_url}/fetch/alias_symbol/{gene_symbol}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("response", {}).get("docs"):
                    doc = data["response"]["docs"][0]
                    return {
                        "success": True,
                        "symbol": doc.get("symbol", ""),
                        "hgnc_id": doc.get("hgnc_id", ""),
                        "aliases": doc.get("alias_symbol", [])
                    }
                    
            return {"success": False, "error": "No matches found in HGNC"}
            
        except Exception as e:
            logger.error(f"HGNC API error for '{gene_symbol}': {e}")
            return {"success": False, "error": str(e)}
            
    def _try_fuzzy_matching(self, gene_symbol: str) -> dict[str, Any]:
        """Try various fuzzy matching strategies"""
        
        # Strategy 1: Remove hyphens/underscores
        if '-' in gene_symbol or '_' in gene_symbol:
            clean_symbol = re.sub(r'[-_]', '', gene_symbol)
            result = self._lookup_hgnc_api(clean_symbol)
            if result["success"]:
                return result
                
        # Strategy 2: Add/remove common suffixes
        suffixes_to_try = ['', '1', 'A', 'B', 'C']
        for suffix in suffixes_to_try:
            if gene_symbol.endswith(suffix) and len(suffix) > 0:
                # Try without suffix
                test_symbol = gene_symbol[:-len(suffix)]
                if test_symbol:
                    result = self._lookup_hgnc_api(test_symbol)
                    if result["success"]:
                        return result
            else:
                # Try with suffix
                test_symbol = gene_symbol + suffix
                result = self._lookup_hgnc_api(test_symbol)
                if result["success"]:
                    return result
                    
        # Strategy 3: Search by wildcards (limited to avoid too many results)
        if len(gene_symbol) >= 3:
            try:
                response = self.client.get(
                    f"{self.base_url}/search/symbol/{gene_symbol}*",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    docs = data.get("response", {}).get("docs", [])
                    # Only accept if we get exactly one match to avoid ambiguity
                    if len(docs) == 1:
                        doc = docs[0]
                        return {
                            "success": True,
                            "symbol": doc.get("symbol", ""),
                            "hgnc_id": doc.get("hgnc_id", ""),
                            "aliases": doc.get("alias_symbol", [])
                        }
                        
            except Exception as e:
                logger.debug(f"Fuzzy search error for '{gene_symbol}': {e}")
                
        return {"success": False, "error": "No fuzzy matches found"}
        
    def close(self):
        """Close HTTP client"""
        self.client.close()


def normalize_gene_for_database(db: Session, 
                              gene_text: str, 
                              source_name: str,
                              original_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Central function to normalize genes before database insertion
    
    This function should be called by ALL data sources before creating genes.
    It ensures proper HGNC normalization and handles staging for manual review.
    
    Args:
        db: Database session
        gene_text: Raw gene text from data source
        source_name: Name of data source
        original_data: Original context data for logging
        
    Returns:
        Dictionary with normalization results and database actions taken
    """
    from app.crud.gene_staging import staging_crud, log_crud
    
    start_time = datetime.now(timezone.utc)
    normalizer = GeneNormalizer()
    
    try:
        # Normalize the gene
        result = normalizer.normalize_gene_symbol(gene_text, source_name, original_data)
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Count API calls made from normalization log
        api_calls = 1 if result["normalization_log"].get("hgnc_api_called", False) else 0
        
        if result["success"]:
            # Gene successfully normalized
            logger.info(f"Successfully normalized '{gene_text}' -> {result['approved_symbol']} ({result['hgnc_id']})")
            
            # Log successful normalization
            log_crud.create_log_entry(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                success=True,
                normalization_log=result["normalization_log"],
                approved_symbol=result["approved_symbol"],
                hgnc_id=result["hgnc_id"],
                api_calls_made=api_calls,
                processing_time_ms=processing_time
            )
            
            return {
                "status": "normalized",
                "approved_symbol": result["approved_symbol"],
                "hgnc_id": result["hgnc_id"],
                "aliases": result["aliases"],
                "normalization_log": result["normalization_log"]
            }
            
        elif result["requires_manual_review"]:
            # Gene needs manual review - add to staging table
            logger.warning(f"Gene '{gene_text}' from {source_name} requires manual review")
            
            # Create staging record
            staging_record = staging_crud.create_staging_record(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                normalization_log=result["normalization_log"],
                original_data=original_data
            )
            
            # Log failed normalization
            log_crud.create_log_entry(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                success=False,
                normalization_log=result["normalization_log"],
                staging_id=staging_record.id,
                api_calls_made=api_calls,
                processing_time_ms=processing_time
            )
            
            return {
                "status": "requires_manual_review",
                "original_text": gene_text,
                "normalization_log": result["normalization_log"],
                "staging_id": staging_record.id
            }
            
        else:
            # Unexpected state
            logger.error(f"Unexpected normalization state for '{gene_text}': {result}")
            
            # Log error
            log_crud.create_log_entry(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                success=False,
                normalization_log=result["normalization_log"],
                api_calls_made=api_calls,
                processing_time_ms=processing_time
            )
            
            return {
                "status": "error",
                "error": "Unexpected normalization state",
                "normalization_log": result["normalization_log"]
            }
            
    except Exception as e:
        logger.error(f"Error normalizing gene '{gene_text}': {e}")
        processing_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
        
        # Log error
        try:
            log_crud.create_log_entry(
                db=db,
                original_text=gene_text,
                source_name=source_name,
                success=False,
                normalization_log={"error": str(e), "steps": []},
                processing_time_ms=processing_time
            )
        except:
            pass  # Don't fail if logging fails
            
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        normalizer.close()


# Rate limiting for HGNC API calls
def rate_limit_hgnc_calls():
    """Rate limit HGNC API calls to be respectful"""
    time.sleep(0.1)  # 100ms delay between calls