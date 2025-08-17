# HPO API Reimplementation Strategy

## Executive Summary

This document outlines the complete reimplementation of the HPO (Human Phenotype Ontology) data source, obtaining disease information (including OMIM) directly through the HPO API and creating a modular, extensible API client architecture that leverages the full capabilities of the HPO JAX API.

## Architecture Overview

### Core Design Principles

1. **Modular Architecture**: Separate API concerns into logical modules
2. **Cache-First**: Leverage unified cache system for all API calls
3. **Async-Native**: Built for concurrent operations with sync fallbacks
4. **Extensible**: Easy to add new endpoints and functionality
5. **Resilient**: Circuit breakers, retries, and fallback mechanisms

### Module Structure

```
app/core/hpo/
├── __init__.py
├── base.py           # Base HPO API client with common functionality
├── terms.py          # HPO term operations (hierarchy, descendants)
├── annotations.py    # Phenotype-gene-disease annotations
├── genes.py          # Gene-specific operations
├── diseases.py       # Disease-specific operations  
├── search.py         # Search functionality
└── models.py         # Pydantic models for API responses
```

## Detailed Module Specifications

### 1. Base Module (`base.py`)

Provides core HTTP client functionality with caching, retries, and circuit breakers.

```python
class HPOAPIBase:
    """Base class for HPO API interactions."""
    
    BASE_URL = "https://ontology.jax.org/api"
    HPO_BROWSER_URL = "https://hpo.jax.org"
    
    def __init__(self, cache_service: CacheService, http_client: CachedHttpClient):
        self.cache_service = cache_service
        self.http_client = http_client
        self.namespace = "hpo"
    
    async def _get(self, endpoint: str, params: dict = None, cache_key: str = None, ttl: int = None):
        """
        Generic GET request with intelligent caching.
        
        - Uses ETag-based HTTP caching via Hishel
        - Falls back to database cache
        - Implements circuit breaker pattern
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Use cache_key for database fallback
        if not cache_key:
            cache_key = self._generate_cache_key(endpoint, params)
        
        return await self.http_client.get(
            url,
            params=params,
            namespace=self.namespace,
            cache_key=cache_key,
            fallback_ttl=ttl or settings.CACHE_TTL_HPO
        )
    
    def _generate_cache_key(self, endpoint: str, params: dict = None) -> str:
        """Generate consistent cache keys."""
        key_parts = [endpoint]
        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        return hashlib.sha256(":".join(key_parts).encode()).hexdigest()
```

### 2. Terms Module (`terms.py`)

Handles HPO term hierarchy and relationships.

```python
class HPOTerms(HPOAPIBase):
    """HPO term operations and hierarchy traversal."""
    
    async def get_term(self, hpo_id: str) -> HPOTerm:
        """Get detailed information about an HPO term."""
        response = await self._get(
            f"hp/terms/{hpo_id}",
            cache_key=f"term:{hpo_id}",
            ttl=86400 * 30  # 30 days - terms are stable
        )
        return HPOTerm.model_validate(response)
    
    async def get_descendants(self, hpo_id: str, max_depth: int = 10) -> set[str]:
        """
        Get all descendant terms using optimal strategy:
        1. Try descendants endpoint (single call)
        2. Fall back to recursive children traversal
        """
        # Try direct descendants endpoint first
        try:
            response = await self._get(
                f"hp/terms/{hpo_id}/descendants",
                cache_key=f"descendants:{hpo_id}",
                ttl=86400 * 30
            )
            if isinstance(response, list):
                return {item.get("id") for item in response if item.get("id")}
        except Exception as e:
            logger.debug(f"Descendants endpoint failed for {hpo_id}: {e}")
        
        # Fallback to recursive approach
        return await self._get_descendants_recursive(hpo_id, max_depth)
    
    async def _get_descendants_recursive(self, hpo_id: str, max_depth: int) -> set[str]:
        """Recursively collect descendants via children endpoint."""
        descendants = {hpo_id}
        visited = set()
        
        async def collect(term_id: str, depth: int):
            if depth >= max_depth or term_id in visited:
                return
            visited.add(term_id)
            
            try:
                children_response = await self._get(
                    f"hp/terms/{term_id}/children",
                    cache_key=f"children:{term_id}"
                )
                
                for child in children_response:
                    child_id = child.get("id")
                    if child_id and child_id not in descendants:
                        descendants.add(child_id)
                        await collect(child_id, depth + 1)
            except Exception as e:
                logger.warning(f"Failed to get children for {term_id}: {e}")
        
        await collect(hpo_id, 0)
        return descendants
    
    async def get_ancestors(self, hpo_id: str) -> list[str]:
        """Get ancestor terms (parents up to root)."""
        response = await self._get(
            f"hp/terms/{hpo_id}/parents",
            cache_key=f"ancestors:{hpo_id}",
            ttl=86400 * 30
        )
        return [item.get("id") for item in response if item.get("id")]
```

### 3. Annotations Module (`annotations.py`)

Handles phenotype-gene-disease associations.

```python
class HPOAnnotations(HPOAPIBase):
    """Phenotype annotation operations."""
    
    async def get_term_annotations(self, hpo_id: str) -> TermAnnotations:
        """
        Get all annotations for an HPO term.
        Returns genes, diseases, and medical actions.
        """
        response = await self._get(
            f"network/annotation/{hpo_id}",
            cache_key=f"annotations:{hpo_id}",
            ttl=86400 * 7  # 7 days
        )
        return TermAnnotations.model_validate(response)
    
    async def get_disease_annotations(self, disease_id: str) -> DiseaseAnnotations:
        """
        Get annotations for a disease (e.g., OMIM:123456, ORPHA:789).
        Includes phenotypes, genes, inheritance patterns.
        """
        response = await self._get(
            f"network/annotation/{disease_id}",
            cache_key=f"disease:{disease_id}",
            ttl=86400 * 7
        )
        
        # Extract inheritance from categories
        inheritance = []
        if "categories" in response and "Inheritance" in response["categories"]:
            inheritance = response["categories"]["Inheritance"]
        
        return DiseaseAnnotations(
            disease_id=disease_id,
            disease_name=response.get("disease", {}).get("name"),
            genes=response.get("genes", []),
            phenotypes=response.get("categories", {}),
            inheritance=inheritance
        )
    
    async def batch_get_annotations(self, hpo_ids: list[str], batch_size: int = 10) -> dict:
        """
        Efficiently fetch annotations for multiple HPO terms.
        Uses concurrent requests with batching.
        """
        results = {}
        
        for i in range(0, len(hpo_ids), batch_size):
            batch = hpo_ids[i:i + batch_size]
            tasks = [self.get_term_annotations(hpo_id) for hpo_id in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for hpo_id, result in zip(batch, batch_results):
                if not isinstance(result, Exception):
                    results[hpo_id] = result
                else:
                    logger.warning(f"Failed to get annotations for {hpo_id}: {result}")
        
        return results
```

### 4. Genes Module (`genes.py`)

Gene-specific operations using HPO browser API.

```python
class HPOGenes(HPOAPIBase):
    """Gene-specific HPO operations."""
    
    async def get_gene_info(self, gene_id: str) -> GeneInfo:
        """
        Get detailed gene information from HPO.
        
        Args:
            gene_id: NCBI Gene ID (e.g., "NCBIGene:8481" or just "8481")
        """
        # Normalize gene ID format
        if not gene_id.startswith("NCBIGene:"):
            gene_id = f"NCBIGene:{gene_id}"
        
        # HPO Browser API endpoint
        response = await self._get(
            f"browse/gene/{gene_id}",
            cache_key=f"gene:{gene_id}",
            ttl=86400 * 7
        )
        
        return GeneInfo.model_validate(response)
    
    async def get_gene_phenotypes(self, gene_id: str) -> list[HPOTerm]:
        """Get all HPO phenotypes associated with a gene."""
        gene_info = await self.get_gene_info(gene_id)
        return gene_info.phenotypes
    
    async def get_gene_diseases(self, gene_id: str) -> list[Disease]:
        """Get all diseases associated with a gene."""
        gene_info = await self.get_gene_info(gene_id)
        return gene_info.diseases
    
    async def search_genes(self, query: str, max_results: int = 100) -> list[Gene]:
        """Search for genes by symbol or name."""
        response = await self._get(
            "search/gene",
            params={"q": query, "max": max_results},
            cache_key=f"gene_search:{query}:{max_results}",
            ttl=86400  # 1 day
        )
        return [Gene.model_validate(item) for item in response.get("genes", [])]
```

### 5. Diseases Module (`diseases.py`)

Disease-specific operations and inheritance extraction.

```python
class HPODiseases(HPOAPIBase):
    """Disease-specific HPO operations."""
    
    async def get_disease_info(self, disease_id: str) -> DiseaseInfo:
        """Get comprehensive disease information."""
        response = await self._get(
            f"network/annotation/{disease_id}",
            cache_key=f"disease_info:{disease_id}",
            ttl=86400 * 7
        )
        
        # Parse inheritance patterns
        inheritance_patterns = self._extract_inheritance(response)
        
        return DiseaseInfo(
            disease_id=disease_id,
            name=response.get("disease", {}).get("name"),
            genes=response.get("genes", []),
            phenotypes=self._extract_phenotypes(response),
            inheritance=inheritance_patterns
        )
    
    def _extract_inheritance(self, response: dict) -> list[InheritancePattern]:
        """Extract and parse inheritance patterns from disease response."""
        patterns = []
        
        categories = response.get("categories", {})
        inheritance_data = categories.get("Inheritance", [])
        
        for item in inheritance_data:
            patterns.append(InheritancePattern(
                hpo_id=item.get("id"),
                name=item.get("name"),
                frequency=item.get("metadata", {}).get("frequency"),
                sources=item.get("metadata", {}).get("sources", [])
            ))
        
        return patterns
    
    def _extract_phenotypes(self, response: dict) -> list[Phenotype]:
        """Extract all phenotypes from disease response."""
        phenotypes = []
        categories = response.get("categories", {})
        
        for category_name, items in categories.items():
            if category_name != "Inheritance":  # Skip inheritance
                for item in items:
                    phenotypes.append(Phenotype(
                        hpo_id=item.get("id"),
                        name=item.get("name"),
                        category=category_name,
                        frequency=item.get("metadata", {}).get("frequency"),
                        onset=item.get("metadata", {}).get("onset")
                    ))
        
        return phenotypes
```

### 6. Search Module (`search.py`)

Unified search functionality across HPO.

```python
class HPOSearch(HPOAPIBase):
    """HPO search operations."""
    
    async def search_all(self, query: str, max_results: int = 100) -> SearchResults:
        """
        Search across terms, genes, and diseases.
        """
        # Run searches in parallel
        tasks = [
            self.search_terms(query, max_results),
            self.search_genes(query, max_results),
            self.search_diseases(query, max_results)
        ]
        
        terms, genes, diseases = await asyncio.gather(*tasks, return_exceptions=True)
        
        return SearchResults(
            terms=terms if not isinstance(terms, Exception) else [],
            genes=genes if not isinstance(genes, Exception) else [],
            diseases=diseases if not isinstance(diseases, Exception) else []
        )
    
    async def search_terms(self, query: str, max_results: int = 100) -> list[HPOTerm]:
        """Search HPO terms."""
        response = await self._get(
            "hp/search",
            params={"q": query, "max": max_results},
            cache_key=f"term_search:{query}:{max_results}",
            ttl=86400
        )
        return [HPOTerm.model_validate(item) for item in response.get("terms", [])]
```

## Data Models (`models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class HPOTerm(BaseModel):
    """HPO term model."""
    id: str
    name: str
    definition: Optional[str] = None
    synonyms: list[str] = Field(default_factory=list)
    is_obsolete: bool = False
    replaced_by: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)

class Gene(BaseModel):
    """Gene model."""
    id: str  # NCBIGene:XXXXX
    symbol: str
    name: Optional[str] = None
    ncbi_gene_id: Optional[int] = None
    
    @property
    def entrez_id(self) -> Optional[int]:
        """Extract numeric Entrez ID."""
        if self.ncbi_gene_id:
            return self.ncbi_gene_id
        if self.id and self.id.startswith("NCBIGene:"):
            try:
                return int(self.id.split(":")[1])
            except (ValueError, IndexError):
                pass
        return None

class Disease(BaseModel):
    """Disease model."""
    id: str  # OMIM:XXXXX or ORPHA:XXXXX
    name: str
    mondo_id: Optional[str] = None
    description: Optional[str] = None

class InheritancePattern(BaseModel):
    """Inheritance pattern model."""
    hpo_id: str
    name: str
    frequency: Optional[str] = None
    sources: list[str] = Field(default_factory=list)

class TermAnnotations(BaseModel):
    """Annotations for an HPO term."""
    term_id: str
    genes: list[Gene] = Field(default_factory=list)
    diseases: list[Disease] = Field(default_factory=list)
    medical_actions: list[dict] = Field(default_factory=list)

class DiseaseAnnotations(BaseModel):
    """Comprehensive disease annotations."""
    disease_id: str
    disease_name: Optional[str] = None
    genes: list[Gene] = Field(default_factory=list)
    phenotypes: dict = Field(default_factory=dict)
    inheritance: list[InheritancePattern] = Field(default_factory=list)
```

## Pipeline Integration

### Main HPO Pipeline (`hpo_pipeline.py`)

```python
class HPOPipeline:
    """Main HPO data processing pipeline."""
    
    def __init__(self, cache_service: CacheService, http_client: CachedHttpClient):
        self.terms = HPOTerms(cache_service, http_client)
        self.annotations = HPOAnnotations(cache_service, http_client)
        self.genes = HPOGenes(cache_service, http_client)
        self.diseases = HPODiseases(cache_service, http_client)
        self.search = HPOSearch(cache_service, http_client)
    
    async def process_kidney_phenotypes(self, tracker: ProgressTracker) -> dict:
        """
        Main pipeline for processing kidney/urinary phenotypes.
        
        1. Get descendants of HP:0010935 (Abnormality of the upper urinary tract)
        2. Fetch annotations for all terms
        3. Process diseases for inheritance
        4. Aggregate gene evidence
        """
        tracker.update_status("Fetching kidney/urinary HPO terms...")
        
        # Step 1: Get all relevant HPO terms
        root_term = settings.HPO_KIDNEY_ROOT_TERM  # HP:0010935
        descendants = await self.terms.get_descendants(root_term, max_depth=10)
        tracker.update_status(f"Found {len(descendants)} kidney-related HPO terms")
        
        # Step 2: Batch fetch annotations
        tracker.update_status("Fetching gene-disease associations...")
        annotations = await self.annotations.batch_get_annotations(
            list(descendants),
            batch_size=10
        )
        
        # Step 3: Aggregate gene data
        gene_evidence = {}
        disease_cache = {}
        
        for hpo_id, term_annotations in annotations.items():
            tracker.update_progress(
                len(gene_evidence),
                len(annotations),
                f"Processing {hpo_id}"
            )
            
            # Process genes
            for gene in term_annotations.genes:
                gene_symbol = gene.symbol
                if gene_symbol not in gene_evidence:
                    gene_evidence[gene_symbol] = {
                        "entrez_id": gene.entrez_id,
                        "hpo_terms": set(),
                        "diseases": set(),
                        "inheritance_patterns": set()
                    }
                gene_evidence[gene_symbol]["hpo_terms"].add(hpo_id)
            
            # Process diseases for inheritance
            for disease in term_annotations.diseases:
                if disease.id not in disease_cache:
                    disease_info = await self.diseases.get_disease_info(disease.id)
                    disease_cache[disease.id] = disease_info
                
                disease_info = disease_cache[disease.id]
                
                # Link inheritance to genes
                for gene in disease_info.genes:
                    if gene.symbol in gene_evidence:
                        gene_evidence[gene.symbol]["diseases"].add(disease.id)
                        for pattern in disease_info.inheritance:
                            gene_evidence[gene.symbol]["inheritance_patterns"].add(
                                pattern.name
                            )
        
        tracker.update_status(f"Processed {len(gene_evidence)} genes")
        return gene_evidence
```

## Usage Examples

### Basic Usage

```python
# Initialize HPO client
cache_service = get_cache_service(db_session)
http_client = get_cached_http_client(cache_service)

hpo = HPOPipeline(cache_service, http_client)

# Get term information
term = await hpo.terms.get_term("HP:0000113")
print(f"Term: {term.name}")

# Get descendants
descendants = await hpo.terms.get_descendants("HP:0010935")
print(f"Found {len(descendants)} descendant terms")

# Get gene information
gene_info = await hpo.genes.get_gene_info("NCBIGene:8481")
print(f"Gene: {gene_info.symbol} - {gene_info.name}")

# Search across HPO
results = await hpo.search.search_all("polycystic kidney")
```

### Pipeline Integration

```python
async def update_hpo_async(db: Session, tracker: ProgressTracker):
    """Update HPO data source."""
    
    # Initialize pipeline
    cache_service = get_cache_service(db)
    http_client = get_cached_http_client(cache_service)
    pipeline = HPOPipeline(cache_service, http_client)
    
    # Process kidney phenotypes
    gene_evidence = await pipeline.process_kidney_phenotypes(tracker)
    
    # Create database entries
    for gene_symbol, evidence in gene_evidence.items():
        # Normalize gene
        gene_info = normalize_gene(gene_symbol)
        
        # Create or update gene
        gene = gene_crud.get_or_create(
            db,
            GeneCreate(
                symbol=gene_info["symbol"],
                name=gene_info["name"],
                entrez_id=evidence["entrez_id"]
            )
        )
        
        # Create evidence
        evidence_entry = GeneEvidence(
            gene_id=gene.id,
            source="HPO",
            evidence_type="phenotype",
            evidence_data={
                "hpo_terms": list(evidence["hpo_terms"]),
                "diseases": list(evidence["diseases"]),
                "inheritance": list(evidence["inheritance_patterns"])
            }
        )
        
        db.add(evidence_entry)
    
    db.commit()
    tracker.update_status("HPO update complete")
```

## Advantages of This Architecture

1. **Modular Design**: Each module handles specific API concerns
2. **Extensibility**: Easy to add new endpoints (e.g., pathway data)
3. **Cache Optimization**: Different TTLs for different data types
4. **Performance**: Batch operations and concurrent requests
5. **Resilience**: Fallback strategies and error handling
6. **Type Safety**: Pydantic models for all API responses
7. **Reusability**: Modules can be used independently

## Migration Strategy

1. **Phase 1**: Implement base modules and models
2. **Phase 2**: Create pipeline with kidney phenotype focus
3. **Phase 3**: Add async support and caching
4. **Phase 4**: Integrate with existing data sources
5. **Phase 5**: Enable auto-update and monitoring

## Configuration

```yaml
# HPO Configuration
HPO:
  api_url: "https://ontology.jax.org/api"
  browser_url: "https://hpo.jax.org"
  root_terms:
    kidney: "HP:0010935"  # Abnormality of the upper urinary tract
    renal: "HP:0000077"   # Abnormality of the kidney
  max_depth: 10
  batch_size: 10
  cache_ttl:
    terms: 2592000  # 30 days
    annotations: 604800  # 7 days
    search: 86400  # 1 day
```

## Testing Strategy

1. **Unit Tests**: Test each module independently
2. **Integration Tests**: Test pipeline with real API
3. **Cache Tests**: Verify caching behavior
4. **Performance Tests**: Benchmark batch operations
5. **Resilience Tests**: Test error handling and fallbacks

## Monitoring and Metrics

- API call count per endpoint
- Cache hit rates by namespace
- Response times per operation
- Error rates and types
- Data freshness indicators

## Future Enhancements

1. **GraphQL Support**: Add GraphQL client for complex queries
2. **Streaming Updates**: WebSocket support for real-time updates
3. **ML Integration**: Phenotype similarity scoring
4. **Graph Analytics**: Network analysis of gene-phenotype relationships
5. **Clinical Decision Support**: Integration with clinical guidelines

## Conclusion

This modular architecture provides a robust, extensible foundation for HPO integration that:
- Obtains disease information (including OMIM) via HPO API
- Maximizes API capabilities
- Ensures optimal performance through caching
- Supports future expansion and enhancement
- Maintains compatibility with existing infrastructure