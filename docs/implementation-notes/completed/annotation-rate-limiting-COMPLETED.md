# Refactoring Plan: Annotation Pipeline Rate Limiting, Logging, and Cache

## Executive Summary

This document outlines the critical refactoring required to fix the annotation pipeline's rate limiting, logging, and caching issues. The primary goal is to leverage our existing `retry_utils.py` infrastructure that is currently unused by any annotation source.

**Key Problems:**
- 78% of genes missing gnomAD data due to rate limiting
- 90% missing ClinVar data
- No annotation sources use our existing retry/backoff system
- Incorrect logging levels (warnings for errors)
- Cache stores bad responses (empty/null data)

**Solution:** Use existing `RetryableHTTPClient` and `@retry_with_backoff` decorator consistently across all annotation sources.

## 1. Base Annotation Source Refactoring

### File: `backend/app/pipeline/sources/annotations/base.py`

#### Changes Required:

**Add imports (line 7, after existing imports):**
```python
from app.core.retry_utils import (
    RetryableHTTPClient,
    RetryConfig,
    retry_with_backoff,
    CircuitBreaker
)
from app.core.cached_http_client import CachedHTTPClient
```

**Add class attributes (line 35, after existing attributes):**
```python
# Retry configuration
retry_config: RetryConfig = None
circuit_breaker: CircuitBreaker = None
http_client: RetryableHTTPClient = None

# Rate limiting
requests_per_second: float = 2.0  # Default 2 req/s
```

**Update `__init__` method (line 40):**
```python
def __init__(self, session: Session):
    """
    Initialize annotation source with retry capabilities.
    
    Args:
        session: SQLAlchemy database session
    """
    self.session = session
    
    if not self.source_name:
        raise ValueError("source_name must be defined in subclass")
    
    # Initialize retry configuration
    self.retry_config = RetryConfig(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
        retry_on_status_codes=(429, 500, 502, 503, 504),
    )
    
    # Initialize circuit breaker
    self.circuit_breaker = CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception=httpx.HTTPStatusError
    )
    
    # Get or create source record
    self.source_record = self._get_or_create_source()
```

**Add new method for HTTP client (line 95):**
```python
async def get_http_client(self) -> RetryableHTTPClient:
    """
    Get or create a RetryableHTTPClient with proper configuration.
    
    Returns:
        Configured HTTP client with retry logic
    """
    if not self.http_client:
        # Check if we should use cached client
        use_cache = self.source_record.config.get("use_http_cache", True)
        
        if use_cache:
            from app.core.cached_http_client import CachedHTTPClient
            base_client = CachedHTTPClient(
                cache_dir=f"/tmp/annotation_cache/{self.source_name}",
                ttl=self.cache_ttl_days * 86400
            )
        else:
            base_client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
            )
        
        self.http_client = RetryableHTTPClient(
            client=base_client,
            retry_config=self.retry_config,
            circuit_breaker=self.circuit_breaker
        )
    
    return self.http_client
```

**Add rate limiting helper (line 120):**
```python
async def apply_rate_limit(self):
    """Apply rate limiting between requests."""
    delay = 1.0 / self.requests_per_second
    await asyncio.sleep(delay)
```

**Update cache validation (line 200, in update_gene method):**
```python
async def update_gene(self, gene: Gene) -> bool:
    """
    Update annotations for a single gene with proper retry and cache validation.
    """
    try:
        cache_service = get_cache_service(self.session)
        cache_key = f"{gene.approved_symbol}:{gene.hgnc_id}"
        
        # Check cache first
        cached_data = await cache_service.get(
            key=cache_key,
            namespace=self.source_name.lower(),
            default=None
        )
        
        # Validate cached data - don't use empty/null responses
        if cached_data and self._is_valid_annotation(cached_data):
            logger.sync_debug(  # Changed from info to debug
                f"Using cached annotation for {gene.approved_symbol}",
                source=self.source_name
            )
            annotation_data = cached_data
            metadata = {
                "retrieved_at": datetime.utcnow().isoformat(),
                "from_cache": True
            }
        else:
            # Fetch from source with retry
            annotation_data = await self.fetch_annotation(gene)
            
            # Only cache valid responses
            if annotation_data and self._is_valid_annotation(annotation_data):
                await cache_service.set(
                    key=cache_key,
                    value=annotation_data,
                    namespace=self.source_name.lower(),
                    ttl=self.cache_ttl_days * 86400
                )
                metadata = {
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "from_cache": False
                }
            else:
                # Don't cache invalid responses
                logger.sync_warning(  # Keep as warning for missing data
                    f"Invalid or missing annotation for {gene.approved_symbol}",
                    source=self.source_name
                )
                return False
        
        if annotation_data:
            self.store_annotation(gene, annotation_data, metadata=metadata)
            return True
        
        return False
        
    except Exception as e:
        logger.sync_error(  # Changed from warning to error
            f"Error updating gene {gene.approved_symbol}: {str(e)}",
            source=self.source_name,
            gene_id=gene.id
        )
        return False
```

**Add validation method (line 250):**
```python
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """
    Validate annotation data to ensure it's not empty or error response.
    Override in subclasses for source-specific validation.
    """
    if not annotation_data:
        return False
    
    # Check for common error indicators
    if annotation_data.get("error") or annotation_data.get("status") == "error":
        return False
    
    # Check for empty results
    if isinstance(annotation_data, dict):
        # Must have at least one non-metadata field
        meaningful_keys = [k for k in annotation_data.keys() 
                          if k not in ["source", "version", "timestamp"]]
        return len(meaningful_keys) > 0
    
    return True
```

## 2. gnomAD Source Refactoring

### File: `backend/app/pipeline/sources/annotations/gnomad.py`

#### Changes Required:

**Update class configuration (line 30):**
```python
class GnomADAnnotationSource(BaseAnnotationSource):
    """gnomAD annotation source with proper rate limiting."""
    
    source_name = "gnomad"
    display_name = "gnomAD"
    version = "v4.0.0"
    
    # API configuration
    graphql_url = "https://gnomad.broadinstitute.org/api"
    headers = {"Content-Type": "application/json", "User-Agent": "KidneyGeneticsDB/1.0"}
    
    # Cache configuration
    cache_ttl_days = 30
    
    # Rate limiting - gnomAD allows 10 req/s but we'll be conservative
    requests_per_second = 3.0
    
    # Reference genome
    reference_genome = "GRCh38"
```

**Replace `_execute_query` method (line 188):**
```python
@retry_with_backoff(config=RetryConfig(max_retries=5))
async def _execute_query(self, query: str, variables: dict) -> dict | None:
    """
    Execute a GraphQL query with retry logic and rate limiting.
    """
    # Apply rate limiting
    await self.apply_rate_limit()
    
    # Get configured HTTP client
    client = await self.get_http_client()
    
    try:
        response = await client.post(
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers=self.headers,
        )
        
        data = response.json()
        
        # Check for GraphQL errors
        if data.get("errors"):
            logger.sync_error(  # Keep as error
                "GraphQL errors in gnomAD response",
                errors=data["errors"],
                gene_symbol=variables.get("gene_symbol")
            )
            return None
        
        return data.get("data")
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            # Parse Retry-After header if present
            retry_after = e.response.headers.get("retry-after")
            logger.sync_error(
                "gnomAD rate limit hit",
                status_code=429,
                retry_after=retry_after,
                gene_symbol=variables.get("gene_symbol")
            )
            raise  # Let retry decorator handle it
        else:
            logger.sync_error(
                "gnomAD API error",
                status_code=e.response.status_code,
                gene_symbol=variables.get("gene_symbol")
            )
            raise
            
    except Exception as e:
        logger.sync_error(
            f"Unexpected error querying gnomAD: {str(e)}",
            gene_symbol=variables.get("gene_symbol")
        )
        raise
```

**Update `fetch_batch` method (line 303):**
```python
async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
    """
    Fetch annotations for multiple genes with proper rate limiting.
    """
    results = {}
    failed_genes = []
    
    # Process sequentially with rate limiting instead of concurrent batches
    for i, gene in enumerate(genes):
        try:
            # Show progress
            if i % 10 == 0:
                logger.sync_info(
                    f"Processing gnomAD annotations",
                    progress=f"{i}/{len(genes)}",
                    source=self.source_name
                )
            
            # Fetch with retry logic
            annotation = await self.fetch_annotation(gene)
            
            if annotation and self._is_valid_annotation(annotation):
                results[gene.id] = annotation
            else:
                failed_genes.append(gene.approved_symbol)
                
        except Exception as e:
            logger.sync_error(
                f"Failed to fetch gnomAD annotation for {gene.approved_symbol}",
                error=str(e)
            )
            failed_genes.append(gene.approved_symbol)
            
            # If circuit breaker is open, stop processing
            if self.circuit_breaker and self.circuit_breaker.state == "open":
                logger.sync_error(
                    "Circuit breaker open, stopping batch processing",
                    failed_count=len(failed_genes)
                )
                break
    
    if failed_genes:
        logger.sync_warning(
            f"Failed to fetch gnomAD annotations",
            failed_genes=failed_genes[:10],  # Log first 10
            total_failed=len(failed_genes)
        )
    
    return results
```

**Add validation override (line 350):**
```python
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """Validate gnomAD annotation data."""
    if not super()._is_valid_annotation(annotation_data):
        return False
    
    # gnomAD specific: must have at least one constraint score
    constraint_fields = ["pli", "lof_z", "oe_lof", "mis_z", "syn_z"]
    has_constraint = any(
        annotation_data.get(field) is not None 
        for field in constraint_fields
    )
    
    return has_constraint
```

## 3. ClinVar Source Refactoring

### File: `backend/app/pipeline/sources/annotations/clinvar.py`

#### Changes Required:

**Update class configuration (line 30):**
```python
class ClinVarAnnotationSource(BaseAnnotationSource):
    """ClinVar annotation source with proper rate limiting."""
    
    source_name = "clinvar"
    display_name = "ClinVar"
    version = "1.0"
    
    # Cache configuration
    cache_ttl_days = 7
    
    # API configuration
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    batch_size = 200
    search_batch_size = 10000
    
    # NCBI rate limit: 3 requests per second without API key
    requests_per_second = 2.5  # Conservative to avoid hitting limits
```

**Replace `_search_variants` method (line 79):**
```python
@retry_with_backoff(config=RetryConfig(max_retries=5))
async def _search_variants(self, gene_symbol: str) -> list[str]:
    """
    Search for ClinVar variants with retry logic.
    """
    await self.apply_rate_limit()
    client = await self.get_http_client()
    
    try:
        search_url = f"{self.base_url}/esearch.fcgi"
        params = {
            "db": "clinvar",
            "term": f"{gene_symbol}[gene] AND single_gene[prop]",
            "retmax": self.search_batch_size,
            "retmode": "json",
        }
        
        response = await client.get(search_url, params=params)
        data = response.json()
        
        id_list = data.get("esearchresult", {}).get("idlist", [])
        
        logger.sync_info(  # Changed from info to debug for less noise
            f"Found {len(id_list)} ClinVar variants",
            gene_symbol=gene_symbol
        )
        
        return id_list
        
    except httpx.HTTPStatusError as e:
        logger.sync_error(  # Changed from warning to error
            f"Failed to search ClinVar variants",
            gene_symbol=gene_symbol,
            status_code=e.response.status_code,
            response=e.response.text[:200]
        )
        raise  # Let retry decorator handle it
        
    except Exception as e:
        logger.sync_error(
            f"Error searching ClinVar variants",
            gene_symbol=gene_symbol,
            error=str(e)
        )
        raise
```

**Replace `_fetch_variant_batch` method (line 181):**
```python
@retry_with_backoff(config=RetryConfig(max_retries=5))
async def _fetch_variant_batch(self, variant_ids: list[str]) -> list[dict[str, Any]]:
    """
    Fetch variant details with retry logic and rate limiting.
    """
    if not variant_ids:
        return []
    
    await self.apply_rate_limit()
    client = await self.get_http_client()
    
    try:
        summary_url = f"{self.base_url}/esummary.fcgi"
        params = {
            "db": "clinvar",
            "id": ",".join(variant_ids),
            "retmode": "json"
        }
        
        response = await client.get(summary_url, params=params)
        data = response.json()
        
        result = data.get("result", {})
        
        # Parse each variant
        variants = []
        for uid in result.get("uids", []):
            if uid in result:
                variant = self._parse_variant(result[uid])
                variants.append(variant)
        
        return variants
        
    except httpx.HTTPStatusError as e:
        # Check rate limit headers
        if e.response.status_code == 429 or "X-RateLimit-Remaining" in e.response.headers:
            remaining = e.response.headers.get("X-RateLimit-Remaining", "unknown")
            logger.sync_error(
                f"ClinVar rate limit hit",
                status_code=e.response.status_code,
                remaining_requests=remaining,
                batch_size=len(variant_ids)
            )
        else:
            logger.sync_error(  # Changed from warning to error
                f"Failed to fetch ClinVar variant details",
                status_code=e.response.status_code,
                batch_size=len(variant_ids)
            )
        raise
        
    except Exception as e:
        logger.sync_error(
            f"Error fetching ClinVar variant batch",
            error=str(e),
            batch_size=len(variant_ids)
        )
        raise
```

**Update `fetch_annotation` method with progress (line 324):**
```python
async def fetch_annotation(self, gene: Gene) -> dict[str, Any] | None:
    """
    Fetch ClinVar annotation with progress tracking.
    """
    try:
        logger.sync_debug(
            f"Fetching ClinVar annotation",
            gene_symbol=gene.approved_symbol
        )
        
        # Step 1: Search for all variant IDs
        variant_ids = await self._search_variants(gene.approved_symbol)
        
        if not variant_ids:
            # No variants is valid data, not an error
            logger.sync_debug(
                f"No ClinVar variants found",
                gene_symbol=gene.approved_symbol
            )
            return self._create_empty_annotation(gene)
        
        # Step 2: Fetch variant details in batches with progress
        all_variants = []
        total_batches = (len(variant_ids) + self.batch_size - 1) // self.batch_size
        
        for batch_num, i in enumerate(range(0, len(variant_ids), self.batch_size)):
            batch_ids = variant_ids[i : i + self.batch_size]
            
            # Show progress
            logger.sync_info(
                f"Fetching ClinVar variants",
                gene_symbol=gene.approved_symbol,
                batch=f"{batch_num + 1}/{total_batches}",
                variants=f"{i}/{len(variant_ids)}"
            )
            
            try:
                batch_variants = await self._fetch_variant_batch(batch_ids)
                all_variants.extend(batch_variants)
            except Exception as e:
                logger.sync_error(
                    f"Failed to fetch variant batch",
                    gene_symbol=gene.approved_symbol,
                    batch=batch_num,
                    error=str(e)
                )
                # Continue with partial data rather than failing completely
                if self.circuit_breaker and self.circuit_breaker.state == "open":
                    logger.sync_error("Circuit breaker open, using partial data")
                    break
        
        # Step 3: Aggregate statistics
        stats = self._aggregate_variants(all_variants)
        
        # Build annotation
        annotation = self._build_annotation(gene, stats)
        
        logger.sync_info(
            f"ClinVar annotation complete",
            gene_symbol=gene.approved_symbol,
            total_variants=len(all_variants),
            has_pathogenic=annotation.get("has_pathogenic", False)
        )
        
        return annotation
        
    except Exception as e:
        logger.sync_error(
            f"Error fetching ClinVar annotation",
            gene_symbol=gene.approved_symbol,
            error=str(e)
        )
        return None
```

**Add helper methods (line 400):**
```python
def _create_empty_annotation(self, gene: Gene) -> dict:
    """Create valid empty annotation for genes with no variants."""
    return {
        "gene_symbol": gene.approved_symbol,
        "total_variants": 0,
        "variant_summary": "No variants",
        "pathogenic_count": 0,
        "likely_pathogenic_count": 0,
        "vus_count": 0,
        "benign_count": 0,
        "likely_benign_count": 0,
        "conflicting_count": 0,
        "has_pathogenic": False,
        "pathogenic_percentage": 0,
        "high_confidence_percentage": 0,
        "top_traits": [],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

def _build_annotation(self, gene: Gene, stats: dict) -> dict:
    """Build annotation from aggregated stats."""
    annotation = {
        "gene_symbol": gene.approved_symbol,
        "total_variants": stats["total_count"],
        "pathogenic_count": stats["pathogenic_count"],
        "likely_pathogenic_count": stats["likely_pathogenic_count"],
        "vus_count": stats["vus_count"],
        "benign_count": stats["benign_count"],
        "likely_benign_count": stats["likely_benign_count"],
        "conflicting_count": stats["conflicting_count"],
        "not_provided_count": stats.get("not_provided_count", 0),
        "has_pathogenic": stats["has_pathogenic"],
        "pathogenic_percentage": stats["pathogenic_percentage"],
        "high_confidence_count": stats["high_confidence_count"],
        "high_confidence_percentage": stats["high_confidence_percentage"],
        "variant_types": stats["variant_type_counts"],
        "top_traits": stats["top_traits"],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    
    # Generate summary text
    if stats["has_pathogenic"]:
        p_count = stats["pathogenic_count"] + stats["likely_pathogenic_count"]
        annotation["variant_summary"] = f"{p_count} pathogenic/likely pathogenic variants"
    elif stats["vus_count"] > 0:
        annotation["variant_summary"] = f"{stats['vus_count']} VUS variants"
    else:
        annotation["variant_summary"] = "No pathogenic variants"
    
    return annotation

def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """Validate ClinVar annotation data."""
    if not super()._is_valid_annotation(annotation_data):
        return False
    
    # ClinVar specific: must have variant counts
    required_fields = ["total_variants", "gene_symbol"]
    has_required = all(
        field in annotation_data 
        for field in required_fields
    )
    
    return has_required
```

## 4. HPO Annotation Source Refactoring

### File: `backend/app/pipeline/sources/annotations/hpo.py`

#### Changes Required:

**Update class configuration (line 30):**
```python
class HPOAnnotationSource(BaseAnnotationSource):
    """HPO phenotype annotations with proper rate limiting."""
    
    source_name = "hpo"
    display_name = "Human Phenotype Ontology"
    version = "1.0"
    
    # Cache configuration
    cache_ttl_days = 7
    
    # API endpoints
    hpo_api_url = "https://ontology.jax.org/api"
    
    # Rate limiting - JAX HPO API is generous
    requests_per_second = 10.0
```

**Replace search_gene_for_ncbi_id method (line 60):**
```python
@retry_with_backoff(config=RetryConfig(max_retries=3))
async def search_gene_for_ncbi_id(self, gene_symbol: str) -> str | None:
    """
    Search for a gene symbol with retry logic.
    """
    await self.apply_rate_limit()
    client = await self.get_http_client()
    
    try:
        search_url = f"{self.hpo_api_url}/network/search/gene"
        params = {
            "q": gene_symbol,
            "limit": -1
        }
        
        response = await client.get(search_url, params=params)
        data = response.json()
        
        results = data.get("results", [])
        
        # Find exact match first
        for gene_result in results:
            if gene_result.get("name") == gene_symbol:
                gene_id = gene_result.get("id", "")
                if gene_id.startswith("NCBIGene:"):
                    return gene_id.replace("NCBIGene:", "")
        
        # Try case-insensitive match
        for gene_result in results:
            if gene_result.get("name", "").upper() == gene_symbol.upper():
                gene_id = gene_result.get("id", "")
                if gene_id.startswith("NCBIGene:"):
                    return gene_id.replace("NCBIGene:", "")
        
        logger.sync_debug(
            f"No NCBI Gene ID found for {gene_symbol}",
            results_count=len(results)
        )
        return None
        
    except httpx.HTTPStatusError as e:
        logger.sync_error(
            f"HPO gene search failed",
            gene_symbol=gene_symbol,
            status_code=e.response.status_code
        )
        raise
    except Exception as e:
        logger.sync_error(
            f"Error searching HPO for gene",
            gene_symbol=gene_symbol,
            error=str(e)
        )
        raise
```

**Update all other API methods similarly (fetch_gene_phenotypes, get_phenotype_details, etc.)**

**Add validation override:**
```python
def _is_valid_annotation(self, annotation_data: dict) -> bool:
    """Validate HPO annotation data."""
    if not super()._is_valid_annotation(annotation_data):
        return False
    
    # HPO specific: must have gene_symbol and at least empty arrays
    required_fields = ["gene_symbol", "associated_hpo_terms", "associated_diseases"]
    has_required = all(
        field in annotation_data 
        for field in required_fields
    )
    
    return has_required
```

## 5. MPO/MGI Annotation Source Refactoring

### File: `backend/app/pipeline/sources/annotations/mpo_mgi.py`

#### Changes Required:

**Update class configuration:**
```python
class MPOMGIAnnotationSource(BaseAnnotationSource):
    """Mouse phenotype annotations with proper rate limiting."""
    
    source_name = "mpo_mgi"
    display_name = "MPO/MGI Mouse Phenotypes"
    version = "1.0"
    
    # Cache configuration
    cache_ttl_days = 14
    
    # API configuration
    mgi_api_url = "http://www.informatics.jax.org"
    alliance_api_url = "https://www.alliancegenome.org/api"
    
    # Rate limiting - MGI servers are slower
    requests_per_second = 2.0
```

**Apply @retry_with_backoff to all API methods**

**Example for search_ortholog method:**
```python
@retry_with_backoff(config=RetryConfig(max_retries=3))
async def search_ortholog(self, human_gene_symbol: str) -> dict | None:
    """
    Search for mouse ortholog with retry logic.
    """
    await self.apply_rate_limit()
    client = await self.get_http_client()
    
    try:
        search_url = f"{self.alliance_api_url}/search"
        params = {
            "category": "gene",
            "q": human_gene_symbol,
            "limit": 50
        }
        
        response = await client.get(search_url, params=params)
        data = response.json()
        
        # Process results...
        return ortholog_data
        
    except httpx.HTTPStatusError as e:
        logger.sync_error(
            f"Alliance API search failed",
            gene_symbol=human_gene_symbol,
            status_code=e.response.status_code
        )
        raise
    except Exception as e:
        logger.sync_error(
            f"Error searching for mouse ortholog",
            gene_symbol=human_gene_symbol,
            error=str(e)
        )
        raise
```

## 6. HGNC Annotation Source Refactoring

### File: `backend/app/pipeline/sources/annotations/hgnc.py`

**Note: HGNC may already be implemented differently as it's primarily for gene normalization, but should still use retry logic**

#### Changes Required:

**Update class configuration:**
```python
class HGNCAnnotationSource(BaseAnnotationSource):
    """HGNC gene nomenclature with proper rate limiting."""
    
    source_name = "hgnc"
    display_name = "HGNC Gene Nomenclature"
    version = "1.0"
    
    # Cache configuration
    cache_ttl_days = 30  # HGNC updates monthly
    
    # API configuration
    hgnc_api_url = "https://rest.genenames.org"
    
    # Rate limiting - HGNC has no strict limits but be respectful
    requests_per_second = 5.0
```

**Apply retry logic to API calls**

## 7. STRING PPI Source Refactoring

### File: `backend/app/pipeline/sources/annotations/string_ppi.py`

#### Changes Required:

**Update class configuration:**
```python
class StringPPIAnnotationSource(BaseAnnotationSource):
    """STRING protein interaction with proper rate limiting."""
    
    source_name = "string_ppi"
    display_name = "STRING Protein Interactions"
    version = "12.0"
    
    # Cache configuration
    cache_ttl_days = 14
    
    # API configuration
    string_api_url = "https://string-db.org/api"
    
    # Rate limiting - STRING allows reasonable traffic
    requests_per_second = 5.0
    
    # Batch configuration
    batch_size = 20  # Process proteins in smaller batches
```

**Replace fetch methods with retry logic:**
```python
@retry_with_backoff(config=RetryConfig(max_retries=3))
async def fetch_protein_id(self, gene_symbol: str) -> str | None:
    """
    Map gene symbol to STRING protein ID with retry.
    """
    await self.apply_rate_limit()
    client = await self.get_http_client()
    
    try:
        map_url = f"{self.string_api_url}/json/get_string_ids"
        params = {
            "identifiers": gene_symbol,
            "species": 9606,  # Human
            "limit": 1,
            "format": "json"
        }
        
        response = await client.get(map_url, params=params)
        data = response.json()
        
        if data and len(data) > 0:
            return data[0].get("stringId")
        
        return None
        
    except httpx.HTTPStatusError as e:
        logger.sync_error(
            f"STRING API mapping failed",
            gene_symbol=gene_symbol,
            status_code=e.response.status_code
        )
        raise
    except Exception as e:
        logger.sync_error(
            f"Error mapping gene to STRING ID",
            gene_symbol=gene_symbol,
            error=str(e)
        )
        raise
```

## 8. GTEx Expression Source Refactoring

### File: `backend/app/pipeline/sources/annotations/gtex.py`

#### Changes Required:

**Update class configuration:**
```python
class GTExAnnotationSource(BaseAnnotationSource):
    """GTEx expression data with proper rate limiting."""
    
    source_name = "gtex"
    display_name = "GTEx Expression"
    version = "v8"
    
    # Cache configuration
    cache_ttl_days = 30  # GTEx is stable
    
    # API configuration
    gtex_api_url = "https://gtexportal.org/api/v2"
    
    # Rate limiting - GTEx has moderate limits
    requests_per_second = 3.0
```

**Apply retry logic to all fetch methods**

## 9. Descartes Cell Atlas Source Refactoring

### File: `backend/app/pipeline/sources/annotations/descartes.py`

#### Changes Required:

**Update class configuration:**
```python
class DescartesAnnotationSource(BaseAnnotationSource):
    """Descartes cell atlas with proper rate limiting."""
    
    source_name = "descartes"
    display_name = "Descartes Cell Atlas"
    version = "1.0"
    
    # Cache configuration
    cache_ttl_days = 30  # Stable dataset
    
    # API configuration
    descartes_api_url = "https://descartes.brotmanbaty.org/api"
    
    # Rate limiting
    requests_per_second = 5.0
```

**Apply retry logic and validation**

## 10. Pipeline Orchestrator Updates

### File: `backend/app/pipeline/annotation_pipeline.py`

**Update `_update_source` method (line 240):**
```python
async def _update_source(
    self, source_name: str, genes: list[Gene], force: bool, current_step: int, total_steps: int
) -> dict[str, Any]:
    """
    Update annotations with better error handling and progress.
    """
    source_class = self.sources[source_name]
    source = source_class(self.db)
    
    successful = 0
    failed = 0
    failed_genes = []
    
    # Show source-level progress
    logger.sync_info(
        f"Starting {source_name} annotation update",
        total_genes=len(genes),
        force_update=force
    )
    
    # Check circuit breaker status
    if source.circuit_breaker and source.circuit_breaker.state == "open":
        logger.sync_warning(
            f"Skipping {source_name} - circuit breaker is open",
            failure_count=source.circuit_breaker.failure_count
        )
        return {"successful": 0, "failed": len(genes), "skipped": True}
    
    # Process genes
    for i, gene in enumerate(genes):
        if self.progress_tracker and i % 50 == 0:
            progress = int(((current_step + i) / total_steps) * 100)
            self.progress_tracker.update(
                current_item=progress,
                operation=f"Updating {source_name}: {i}/{len(genes)} genes",
            )
        
        try:
            success = await source.update_gene(gene)
            if success:
                successful += 1
            else:
                failed += 1
                failed_genes.append(gene.approved_symbol)
                
        except Exception as e:
            logger.sync_error(
                f"Error updating {source_name} for {gene.approved_symbol}",
                error=str(e)
            )
            failed += 1
            failed_genes.append(gene.approved_symbol)
    
    # Log summary
    logger.sync_info(
        f"Completed {source_name} update",
        successful=successful,
        failed=failed,
        success_rate=f"{(successful/len(genes)*100):.1f}%" if genes else "N/A"
    )
    
    if failed_genes:
        logger.sync_warning(
            f"Failed genes for {source_name}",
            sample=failed_genes[:10],
            total_failed=len(failed_genes)
        )
    
    # Update source metadata
    source_record = source.source_record
    source_record.last_update = datetime.utcnow()
    source_record.next_update = datetime.utcnow() + timedelta(days=source.cache_ttl_days)
    self.db.commit()
    
    return {
        "successful": successful,
        "failed": failed,
        "total": len(genes),
        "success_rate": (successful/len(genes)*100) if genes else 0
    }
```

## 11. Configuration Updates

### File: `backend/app/core/datasource_config.py`

**Add annotation source configurations:**
```python
ANNOTATION_SOURCE_CONFIG = {
    "gnomad": {
        "requests_per_second": 3.0,
        "max_retries": 5,
        "cache_ttl_days": 30,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
    },
    "clinvar": {
        "requests_per_second": 2.5,  # NCBI limit without API key
        "max_retries": 5,
        "cache_ttl_days": 7,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
    },
    "hpo": {
        "requests_per_second": 10.0,
        "max_retries": 3,
        "cache_ttl_days": 7,
        "use_http_cache": True,
        "circuit_breaker_threshold": 5,
    },
    "mpo_mgi": {
        "requests_per_second": 2.0,  # MGI servers are slower
        "max_retries": 3,
        "cache_ttl_days": 14,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "hgnc": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 30,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "string_ppi": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 14,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "gtex": {
        "requests_per_second": 3.0,
        "max_retries": 3,
        "cache_ttl_days": 30,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
    "descartes": {
        "requests_per_second": 5.0,
        "max_retries": 3,
        "cache_ttl_days": 30,
        "use_http_cache": True,
        "circuit_breaker_threshold": 3,
    },
}
```

## 12. Testing Strategy

### Create test file: `backend/tests/test_annotation_retry.py`

```python
"""Test annotation sources use retry logic correctly."""

import pytest
import httpx
from unittest.mock import Mock, patch, AsyncMock
from app.pipeline.sources.annotations.gnomad import GnomADAnnotationSource
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.models.gene import Gene


@pytest.mark.asyncio
async def test_gnomad_retries_on_429(db_session):
    """Test gnomAD retries on rate limit."""
    source = GnomADAnnotationSource(db_session)
    
    # Mock gene
    gene = Mock(spec=Gene)
    gene.approved_symbol = "TEST1"
    gene.id = 1
    
    # Mock HTTP responses: first 429, then success
    with patch.object(source, 'get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_client.return_value = mock_http
        
        # First call raises 429
        mock_http.post.side_effect = [
            httpx.HTTPStatusError(
                "Rate limited",
                request=Mock(),
                response=Mock(status_code=429, headers={})
            ),
            Mock(json=lambda: {"data": {"gene": {"gnomad_constraint": {"pLI": 0.9}}}})
        ]
        
        # Should retry and succeed
        result = await source.fetch_annotation(gene)
        
        assert result is not None
        assert mock_http.post.call_count == 2


@pytest.mark.asyncio
async def test_clinvar_validates_cache(db_session):
    """Test ClinVar doesn't cache invalid responses."""
    source = ClinVarAnnotationSource(db_session)
    
    # Test invalid responses aren't cached
    invalid_responses = [
        None,
        {},
        {"error": "Not found"},
        {"total_variants": None},
    ]
    
    for response in invalid_responses:
        assert not source._is_valid_annotation(response)
    
    # Test valid response is cached
    valid_response = {
        "gene_symbol": "TEST1",
        "total_variants": 5,
        "pathogenic_count": 2,
    }
    
    assert source._is_valid_annotation(valid_response)


@pytest.mark.asyncio
async def test_circuit_breaker_opens(db_session):
    """Test circuit breaker opens after failures."""
    source = GnomADAnnotationSource(db_session)
    
    # Force multiple failures
    with patch.object(source, 'get_http_client') as mock_client:
        mock_http = AsyncMock()
        mock_client.return_value = mock_http
        
        # All calls fail
        mock_http.post.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=Mock(),
            response=Mock(status_code=500, headers={})
        )
        
        genes = [Mock(spec=Gene, approved_symbol=f"TEST{i}", id=i) for i in range(10)]
        
        # Process batch
        results = await source.fetch_batch(genes)
        
        # Circuit breaker should be open after threshold
        assert source.circuit_breaker.state == "open"
        assert len(results) == 0


@pytest.mark.asyncio 
async def test_rate_limiting_applied(db_session):
    """Test rate limiting is applied between requests."""
    source = ClinVarAnnotationSource(db_session)
    source.requests_per_second = 10.0  # 10 req/s = 0.1s delay
    
    import time
    start = time.time()
    
    # Make 3 requests
    for _ in range(3):
        await source.apply_rate_limit()
    
    elapsed = time.time() - start
    
    # Should take at least 0.3 seconds
    assert elapsed >= 0.3
```

## 13. Implementation Order

1. **Phase 1: Base Infrastructure (Day 1)**
   - Update `base.py` with retry infrastructure
   - Add configuration to `datasource_config.py`
   - Create unit tests

2. **Phase 2: Critical Sources (Day 2)**
   - Fix gnomAD source (highest impact - 78% missing)
   - Fix ClinVar source (90% missing)
   - Test with subset of genes

3. **Phase 3: Other Sources (Day 3)**
   - Fix HPO, MPO/MGI, HGNC sources
   - Fix STRING PPI (99.9% missing)
   - Update GTEx, Descartes
   - Full integration test

4. **Phase 4: Monitoring (Day 4)**
   - Add metrics collection
   - Create dashboard for monitoring
   - Document runbook for failures

## 14. Rollback Plan

If issues arise:

1. **Immediate:** Set circuit breakers to open state
2. **Short-term:** Revert to previous version via git
3. **Cache:** Clear corrupted cache entries:
   ```bash
   make db-clean-cache
   redis-cli FLUSHDB  # If using Redis
   ```

## 15. Success Metrics

After implementation:

- **gnomAD coverage**: >95% (from 22%)
- **ClinVar coverage**: >95% (from 10%)
- **STRING coverage**: >90% (from 0.1%)
- **HPO coverage**: >95%
- **API errors**: <1% of requests
- **429 errors**: <0.1% of requests
- **Cache hit rate**: >50%
- **Average retry count**: <2 per request

## 16. Monitoring Queries

```sql
-- Check annotation coverage
SELECT 
    source,
    COUNT(DISTINCT gene_id) as genes_with_annotations,
    ROUND(COUNT(DISTINCT gene_id) * 100.0 / (SELECT COUNT(*) FROM genes), 2) as coverage_percent
FROM gene_annotations
GROUP BY source
ORDER BY coverage_percent DESC;

-- Check recent failures
SELECT 
    level,
    logger_name,
    message,
    COUNT(*) as count
FROM system_logs
WHERE 
    created_at > NOW() - INTERVAL '1 hour'
    AND level IN ('ERROR', 'WARNING')
    AND logger_name LIKE '%annotation%'
GROUP BY level, logger_name, message
ORDER BY count DESC;
```

## Conclusion

This refactoring leverages our existing `retry_utils.py` infrastructure that was built but never used. The key insight is that we don't need to build new retry logic - we just need to USE what we already have.

The changes are surgical and focused:
1. Use `RetryableHTTPClient` instead of raw `httpx.AsyncClient`
2. Add `@retry_with_backoff` decorator to API methods
3. Fix logging levels (error for errors, not warnings)
4. Validate cache entries before storing
5. Add progress indicators consistently

Expected improvement: From 22% gnomAD coverage to >95%, from 10% ClinVar to >95%.