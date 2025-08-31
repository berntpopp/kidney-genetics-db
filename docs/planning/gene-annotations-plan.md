# Gene Annotation Feature Plan

## Executive Summary
Implement an extensible gene annotation system for kidney-genetics-db that supports multiple annotation sources, starting with HGNC and gnomAD data. The system will provide fast access, regular updates, and allow easy addition of new annotation sources over time.

## Architecture Overview

### Database Design

#### Core Tables

1. **gene_annotations** (Main annotation storage)
```sql
CREATE TABLE gene_annotations (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL,  -- 'hgnc', 'gnomad', 'clinvar', etc.
    version VARCHAR(20),           -- Source version/release
    annotations JSONB NOT NULL,    -- Flexible annotation data
    metadata JSONB,                 -- Source metadata (download date, etc.)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(gene_id, source, version)
);

-- Indexes for performance
CREATE INDEX idx_gene_annotations_gene_id ON gene_annotations(gene_id);
CREATE INDEX idx_gene_annotations_source ON gene_annotations(source);
CREATE INDEX idx_gene_annotations_jsonb ON gene_annotations USING GIN(annotations);
```

2. **annotation_sources** (Registry of annotation sources)
```sql
CREATE TABLE annotation_sources (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    base_url VARCHAR(255),
    update_frequency VARCHAR(50),  -- 'daily', 'weekly', 'monthly'
    last_update TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    config JSONB,  -- Source-specific configuration
    created_at TIMESTAMP DEFAULT NOW()
);
```

3. **annotation_history** (Track changes over time)
```sql
CREATE TABLE annotation_history (
    id SERIAL PRIMARY KEY,
    gene_id INTEGER REFERENCES genes(id),
    source VARCHAR(50),
    operation VARCHAR(20),  -- 'insert', 'update', 'delete'
    old_data JSONB,
    new_data JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT NOW()
);
```

#### Materialized Views for Fast Access

```sql
-- Combined annotation view for frequently accessed data
CREATE MATERIALIZED VIEW gene_annotations_summary AS
SELECT 
    g.id as gene_id,
    g.approved_symbol,
    g.hgnc_id,
    -- HGNC annotations
    (hgnc.annotations->>'ncbi_gene_id')::INTEGER as ncbi_gene_id,
    hgnc.annotations->>'mane_select' as mane_select,
    hgnc.annotations->>'ensembl_gene_id' as ensembl_gene_id,
    -- gnomAD constraint scores
    (gnomad.annotations->>'pli')::FLOAT as pli,
    (gnomad.annotations->>'oe_lof')::FLOAT as oe_lof,
    (gnomad.annotations->>'oe_lof_upper')::FLOAT as oe_lof_upper,
    (gnomad.annotations->>'oe_lof_lower')::FLOAT as oe_lof_lower,
    (gnomad.annotations->>'lof_z')::FLOAT as lof_z,
    (gnomad.annotations->>'mis_z')::FLOAT as mis_z,
    (gnomad.annotations->>'syn_z')::FLOAT as syn_z,
    (gnomad.annotations->>'oe_mis')::FLOAT as oe_mis,
    (gnomad.annotations->>'oe_syn')::FLOAT as oe_syn
FROM genes g
LEFT JOIN LATERAL (
    SELECT annotations 
    FROM gene_annotations 
    WHERE gene_id = g.id AND source = 'hgnc' 
    ORDER BY created_at DESC 
    LIMIT 1
) hgnc ON true
LEFT JOIN LATERAL (
    SELECT annotations 
    FROM gene_annotations 
    WHERE gene_id = g.id AND source = 'gnomad' 
    ORDER BY created_at DESC 
    LIMIT 1
) gnomad ON true;

CREATE UNIQUE INDEX idx_gene_annotations_summary_gene_id ON gene_annotations_summary(gene_id);
CREATE INDEX idx_gene_annotations_summary_pli ON gene_annotations_summary(pli);
```

### Data Models (SQLAlchemy)

```python
# backend/app/models/gene_annotation.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class GeneAnnotation(Base, TimestampMixin):
    """Store gene annotations from various sources"""
    __tablename__ = "gene_annotations"
    __table_args__ = (
        UniqueConstraint('gene_id', 'source', 'version', name='unique_gene_source_version'),
    )
    
    id = Column(Integer, primary_key=True)
    gene_id = Column(Integer, ForeignKey("genes.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(50), nullable=False, index=True)
    version = Column(String(20))
    annotations = Column(JSONB, nullable=False)
    metadata = Column(JSONB)
    
    # Relationships
    gene = relationship("Gene", back_populates="annotations")

class AnnotationSource(Base, TimestampMixin):
    """Registry of annotation sources"""
    __tablename__ = "annotation_sources"
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100))
    description = Column(Text)
    base_url = Column(String(255))
    update_frequency = Column(String(50))
    last_update = Column(DateTime)
    is_active = Column(Boolean, default=True)
    config = Column(JSONB)

class AnnotationHistory(Base):
    """Track annotation changes"""
    __tablename__ = "annotation_history"
    
    id = Column(Integer, primary_key=True)
    gene_id = Column(Integer, ForeignKey("genes.id"))
    source = Column(String(50))
    operation = Column(String(20))
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
```

### Annotation Sources Implementation

#### Base Annotation Source Class

```python
# backend/app/pipeline/sources/annotations/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from app.pipeline.sources.unified.base import UnifiedDataSource

class AnnotationSource(UnifiedDataSource, ABC):
    """Base class for all annotation sources"""
    
    @abstractmethod
    async def fetch_annotation(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch annotation for a single gene"""
        pass
    
    @abstractmethod
    async def fetch_annotations_batch(self, gene_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch annotations for multiple genes"""
        pass
    
    @abstractmethod
    def get_source_version(self) -> str:
        """Get current version/release of the data source"""
        pass
    
    async def update_annotations(self, gene_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Update annotations in database"""
        stats = {"processed": 0, "updated": 0, "errors": 0}
        
        # Get genes to update
        if gene_ids:
            genes = await self.get_genes_by_ids(gene_ids)
        else:
            genes = await self.get_all_genes()
        
        # Process in batches
        for batch in self.batch_iterator(genes, self.batch_size):
            symbols = [g.approved_symbol for g in batch]
            annotations = await self.fetch_annotations_batch(symbols)
            
            for gene in batch:
                if gene.approved_symbol in annotations:
                    await self.save_annotation(
                        gene_id=gene.id,
                        data=annotations[gene.approved_symbol],
                        version=self.get_source_version()
                    )
                    stats["updated"] += 1
                stats["processed"] += 1
        
        return stats
```

#### HGNC Annotation Source

```python
# backend/app/pipeline/sources/annotations/hgnc.py

class HGNCAnnotationSource(AnnotationSource):
    """
    HGNC annotation source for gene metadata
    
    Uses HGNC REST API: https://www.genenames.org/help/rest/
    
    Key endpoints:
    - /fetch/symbol/{symbol} - Get single gene by symbol
    - /search/{query} - Search across all fields
    - /search/symbol/{symbol} - Search by symbol (current/previous/alias)
    - /fetch/hgnc_id/{hgnc_id} - Get by HGNC ID
    
    Available fields from HGNC:
    - Core identifiers: hgnc_id, symbol, name, status
    - Cross-references: entrez_id (NCBI Gene), ensembl_gene_id, omim_id, ucsc_id
    - MANE Select: mane_select (transcript identifiers)
    - Previous symbols: prev_symbol (list)
    - Aliases: alias_symbol (list)
    - Gene families: gene_family, gene_family_id
    - Location: location, location_sortable
    - Locus info: locus_group, locus_type
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_name = "hgnc"
        self.namespace = "hgnc_annotations"
        self.base_url = "https://rest.genenames.org"
    
    def _get_default_ttl(self) -> int:
        return 7 * 24 * 3600  # 7 days
    
    async def fetch_annotation(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch HGNC annotation for a gene"""
        cache_key = f"annotation:{gene_symbol}"
        
        async def fetch():
            # Use fetch endpoint for exact symbol match
            response = await self.http_client.get(
                f"{self.base_url}/fetch/symbol/{gene_symbol}",
                headers={"Accept": "application/json"}
            )
            data = response.json()
            
            # Check in response.docs array
            if data.get("response", {}).get("docs"):
                doc = data["response"]["docs"][0]
                return {
                    # Core identifiers
                    "hgnc_id": doc.get("hgnc_id"),
                    "symbol": doc.get("symbol"),
                    "name": doc.get("name"),
                    "status": doc.get("status"),  # "Approved", "Entry Withdrawn", etc.
                    
                    # External references (for annotation enrichment)
                    "ncbi_gene_id": doc.get("entrez_id"),  # NCBI Gene (formerly Entrez)
                    "ensembl_gene_id": doc.get("ensembl_gene_id"),
                    "omim_id": doc.get("omim_id"),  # Can be list
                    "ucsc_id": doc.get("ucsc_id"),
                    "vega_id": doc.get("vega_id"),
                    "ccds_id": doc.get("ccds_id"),  # Consensus CDS
                    
                    # MANE Select - critically important for gnomAD lookup
                    "mane_select": self._parse_mane_select(doc.get("mane_select")),
                    
                    # RefSeq and UniProt
                    "refseq_accession": doc.get("refseq_accession"),  # List of RefSeq IDs
                    "uniprot_ids": doc.get("uniprot_ids", []),
                    
                    # Gene family and grouping
                    "gene_family": doc.get("gene_family"),  # e.g., "Zinc fingers C2H2-type"
                    "gene_family_id": doc.get("gene_family_id"),
                    "gene_group": doc.get("gene_group"),  # e.g., "Protein-coding genes"
                    "gene_group_id": doc.get("gene_group_id"),
                    
                    # Chromosomal location
                    "location": doc.get("location"),  # e.g., "19q13.42"
                    "location_sortable": doc.get("location_sortable"),  # For sorting
                    
                    # Locus information
                    "locus_type": doc.get("locus_type"),  # e.g., "gene with protein product"
                    "locus_group": doc.get("locus_group"),  # e.g., "protein-coding gene"
                    
                    # Previous and alias symbols (important for normalization)
                    "prev_symbols": doc.get("prev_symbol", []),
                    "alias_symbols": doc.get("alias_symbol", []),
                    
                    # Dates
                    "date_approved_reserved": doc.get("date_approved_reserved"),
                    "date_modified": doc.get("date_modified"),
                    "date_symbol_changed": doc.get("date_symbol_changed"),
                    "date_name_changed": doc.get("date_name_changed"),
                    
                    # Additional annotations
                    "enzyme_id": doc.get("enzyme_id"),  # EC number
                    "pubmed_id": doc.get("pubmed_id"),  # List of PMIDs
                    "mgd_id": doc.get("mgd_id"),  # Mouse genome database
                    "rgd_id": doc.get("rgd_id"),  # Rat genome database
                }
            return None
        
        return await self.fetch_with_cache(cache_key, fetch)
    
    def _parse_mane_select(self, mane_data: List[str]) -> Optional[Dict[str, str]]:
        """
        Parse MANE Select data
        
        MANE Select format from HGNC API:
        ["NM_001378454.1", "ENST00000380152.8", "NP_001365383.1", "ENSP00000369497.3"]
        
        This differs from the old pipe-delimited format
        """
        if not mane_data or len(mane_data) < 2:
            return None
        
        result = {
            "refseq_nuc": None,
            "ensembl_nuc": None,
            "refseq_prot": None,
            "ensembl_prot": None,
            "ensembl_transcript_id": None  # Critical for gnomAD lookup
        }
        
        for item in mane_data:
            if item.startswith("NM_"):
                result["refseq_nuc"] = item
            elif item.startswith("ENST"):
                result["ensembl_nuc"] = item
                # Extract transcript ID without version for gnomAD
                result["ensembl_transcript_id"] = item.split(".")[0]
            elif item.startswith("NP_"):
                result["refseq_prot"] = item
            elif item.startswith("ENSP"):
                result["ensembl_prot"] = item
        
        return result if result["ensembl_transcript_id"] else None
    
    async def fetch_annotations_batch(self, gene_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch using HGNC search API
        
        Note: HGNC doesn't have a true batch API, but we can use OR queries
        Limited to ~20 symbols per request for URL length constraints
        """
        results = {}
        batch_size = 20  # HGNC URL length limit
        
        for i in range(0, len(gene_symbols), batch_size):
            batch = gene_symbols[i:i + batch_size]
            
            # Build OR query
            query = " OR ".join([f"symbol:{s}" for s in batch])
            
            response = await self.http_client.get(
                f"{self.base_url}/search/{query}",
                headers={"Accept": "application/json"},
                params={"fields": "symbol,hgnc_id,entrez_id,ensembl_gene_id,mane_select,prev_symbol,alias_symbol"}
            )
            
            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            
            for doc in docs:
                symbol = doc.get("symbol")
                if symbol in batch:
                    results[symbol] = self._format_doc(doc)
        
        return results
```

#### gnomAD Annotation Source

```python
# backend/app/pipeline/sources/annotations/gnomad.py

class GnomADAnnotationSource(AnnotationSource):
    """
    gnomAD constraint scores using GraphQL API
    
    Based on gnomad-link implementation with proper GraphQL queries.
    
    Key metrics:
    - pLI: Probability of Loss-of-function Intolerance (>0.9 = intolerant)
    - oe_lof: Observed/Expected ratio for LoF variants
    - lof_z: Loss-of-function Z-score
    - mis_z: Missense Z-score (>3.09 = intolerant)
    - syn_z: Synonymous Z-score (control)
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_name = "gnomad"
        self.namespace = "gnomad_annotations"
        self.api_url = "https://gnomad.broadinstitute.org/api"
        self.gnomad_version = "v4"
        self.reference_genome = "GRCh38"  # v4 uses GRCh38
    
    def _get_default_ttl(self) -> int:
        return 30 * 24 * 3600  # 30 days (gnomAD updates infrequently)
    
    def get_source_version(self) -> str:
        return f"gnomad_{self.gnomad_version}"
    
    async def fetch_annotation(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch gnomAD constraint scores for a gene using GraphQL API
        
        Two approaches:
        1. Direct query by gene symbol
        2. Query by transcript ID from HGNC MANE Select
        """
        cache_key = f"annotation:{gene_symbol}"
        
        async def fetch():
            # First try: Query gene directly by symbol
            gene_query = """
            query gene($gene_symbol: String, $reference_genome: ReferenceGenomeId!) {
                gene(gene_symbol: $gene_symbol, reference_genome: $reference_genome) {
                    gene_id
                    symbol
                    name
                    canonical_transcript_id
                    chrom
                    start
                    stop
                    strand
                    gnomad_constraint {
                        exp_lof
                        exp_mis
                        exp_syn
                        obs_lof
                        obs_mis
                        obs_syn
                        oe_lof
                        oe_lof_lower
                        oe_lof_upper
                        oe_mis
                        oe_mis_lower
                        oe_mis_upper
                        lof_z
                        mis_z
                        syn_z
                        pli
                    }
                    transcripts {
                        transcript_id
                        transcript_version
                    }
                }
            }
            """
            
            response = await self.http_client.post(
                self.api_url,
                json={
                    "query": gene_query, 
                    "variables": {
                        "gene_symbol": gene_symbol,
                        "reference_genome": self.reference_genome
                    }
                },
                headers={"Content-Type": "application/json"}
            )
            data = response.json()
            
            if "errors" in data:
                logger.error(f"GraphQL errors for {gene_symbol}: {data['errors']}")
                return None
            
            gene_data = data.get("data", {}).get("gene")
            if not gene_data:
                return None
            
            constraint = gene_data.get("gnomad_constraint")
            if not constraint:
                # Try fallback: Query by canonical transcript
                if gene_data.get("canonical_transcript_id"):
                    return await self._fetch_by_transcript(
                        gene_data["canonical_transcript_id"], 
                        gene_symbol
                    )
                return None
            
            return {
                "gene_id": gene_data.get("gene_id"),
                "gene_symbol": gene_data.get("symbol"),
                "canonical_transcript_id": gene_data.get("canonical_transcript_id"),
                "chrom": gene_data.get("chrom"),
                "start": gene_data.get("start"),
                "stop": gene_data.get("stop"),
                # Constraint scores
                "pli": constraint.get("pli"),
                "oe_lof": constraint.get("oe_lof"),
                "oe_lof_upper": constraint.get("oe_lof_upper"),
                "oe_lof_lower": constraint.get("oe_lof_lower"),
                "oe_mis": constraint.get("oe_mis"),
                "oe_mis_upper": constraint.get("oe_mis_upper"),
                "oe_mis_lower": constraint.get("oe_mis_lower"),
                "lof_z": constraint.get("lof_z"),
                "mis_z": constraint.get("mis_z"),
                "syn_z": constraint.get("syn_z"),
                "obs_lof": constraint.get("obs_lof"),
                "exp_lof": constraint.get("exp_lof"),
                "obs_mis": constraint.get("obs_mis"),
                "exp_mis": constraint.get("exp_mis"),
                "obs_syn": constraint.get("obs_syn"),
                "exp_syn": constraint.get("exp_syn"),
                "version": self.gnomad_version
            }
        
        return await self.fetch_with_cache(cache_key, fetch)
    
    async def _fetch_by_transcript(
        self, 
        transcript_id: str, 
        gene_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fallback: Fetch constraint scores by transcript ID
        Used when gene query doesn't return constraint data
        """
        transcript_query = """
        query transcript($transcript_id: String!, $reference_genome: ReferenceGenomeId!) {
            transcript(transcript_id: $transcript_id, reference_genome: $reference_genome) {
                transcript_id
                transcript_version
                gene {
                    gene_id
                    symbol
                    name
                    gnomad_constraint {
                        exp_lof
                        exp_mis
                        exp_syn
                        obs_lof
                        obs_mis
                        obs_syn
                        oe_lof
                        oe_lof_lower
                        oe_lof_upper
                        oe_mis
                        oe_mis_lower
                        oe_mis_upper
                        lof_z
                        mis_z
                        syn_z
                        pli
                    }
                }
            }
        }
        """
        
        response = await self.http_client.post(
            self.api_url,
            json={
                "query": transcript_query,
                "variables": {
                    "transcript_id": transcript_id,
                    "reference_genome": self.reference_genome
                }
            },
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        
        if "errors" in data:
            logger.error(f"GraphQL errors for transcript {transcript_id}: {data['errors']}")
            return None
        
        transcript_data = data.get("data", {}).get("transcript")
        if not transcript_data or not transcript_data.get("gene"):
            return None
        
        gene_data = transcript_data["gene"]
        constraint = gene_data.get("gnomad_constraint")
        if not constraint:
            return None
        
        return {
            "gene_id": gene_data.get("gene_id"),
            "gene_symbol": gene_data.get("symbol"),
            "transcript_id": transcript_id,
            # Constraint scores
            "pli": constraint.get("pli"),
            "oe_lof": constraint.get("oe_lof"),
            "oe_lof_upper": constraint.get("oe_lof_upper"),
            "oe_lof_lower": constraint.get("oe_lof_lower"),
            "oe_mis": constraint.get("oe_mis"),
            "oe_mis_upper": constraint.get("oe_mis_upper"),
            "oe_mis_lower": constraint.get("oe_mis_lower"),
            "lof_z": constraint.get("lof_z"),
            "mis_z": constraint.get("mis_z"),
            "syn_z": constraint.get("syn_z"),
            "obs_lof": constraint.get("obs_lof"),
            "exp_lof": constraint.get("exp_lof"),
            "obs_mis": constraint.get("obs_mis"),
            "exp_mis": constraint.get("exp_mis"),
            "obs_syn": constraint.get("obs_syn"),
            "exp_syn": constraint.get("exp_syn"),
            "version": self.gnomad_version
        }
    
    async def fetch_annotation_with_mane(self, gene_symbol: str) -> Optional[Dict[str, Any]]:
        """
        Alternative approach: Use HGNC MANE Select to get canonical transcript
        
        This ensures we get the MANE Select transcript's constraint scores
        """
        # Get HGNC data with MANE Select
        hgnc_source = HGNCAnnotationSource(
            cache_service=self.cache_service,
            http_client=self.http_client,
            db_session=self.db_session
        )
        hgnc_data = await hgnc_source.fetch_annotation(gene_symbol)
        
        if not hgnc_data or not hgnc_data.get("mane_select"):
            # Fall back to direct gene query
            return await self.fetch_annotation(gene_symbol)
        
        transcript_id = hgnc_data["mane_select"]["ensembl_transcript_id"]
        
        # Query by MANE Select transcript
        result = await self._fetch_by_transcript(transcript_id, gene_symbol)
        if result:
            result["mane_select_transcript"] = transcript_id
        
        return result
    
    async def fetch_annotations_batch(self, gene_symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch fetch annotations
        Note: gnomAD API doesn't support true batch queries, so we fetch individually
        """
        results = {}
        
        # Process in parallel for better performance
        tasks = []
        for symbol in gene_symbols:
            tasks.append(self.fetch_annotation(symbol))
        
        annotations = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, annotation in zip(gene_symbols, annotations):
            if isinstance(annotation, Exception):
                logger.error(f"Failed to fetch gnomAD for {symbol}: {annotation}")
                results[symbol] = None
            else:
                results[symbol] = annotation
        
        return results
```

### API Endpoints

#### Annotation Management Endpoints

```python
# backend/app/api/endpoints/annotations.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from app.api.deps import SessionDep, CurrentUser
from app.schemas.annotation import (
    AnnotationResponse, 
    AnnotationUpdate,
    AnnotationSourceResponse,
    AnnotationBatchRequest
)

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

@router.get("/sources", response_model=List[AnnotationSourceResponse])
async def list_annotation_sources(
    session: SessionDep,
    active_only: bool = True
):
    """List all available annotation sources"""
    sources = await crud.annotation_source.get_multi(
        session, 
        filter_active=active_only
    )
    return sources

@router.get("/gene/{gene_id}", response_model=Dict[str, AnnotationResponse])
async def get_gene_annotations(
    gene_id: int,
    session: SessionDep,
    sources: Optional[List[str]] = Query(None),
    latest_only: bool = True
):
    """Get all annotations for a specific gene"""
    annotations = await crud.gene_annotation.get_by_gene(
        session,
        gene_id=gene_id,
        sources=sources,
        latest_only=latest_only
    )
    return annotations

@router.post("/update/{source}")
async def trigger_annotation_update(
    source: str,
    session: SessionDep,
    current_user: CurrentUser,
    gene_ids: Optional[List[int]] = None,
    force: bool = False
):
    """Trigger annotation update for specific source"""
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    # Initialize source
    source_class = get_annotation_source(source)
    if not source_class:
        raise HTTPException(404, f"Unknown annotation source: {source}")
    
    source_instance = source_class(
        db_session=session,
        force_refresh=force
    )
    
    # Run update
    stats = await source_instance.update_annotations(gene_ids)
    
    return {
        "source": source,
        "stats": stats,
        "timestamp": datetime.utcnow()
    }

@router.post("/batch", response_model=Dict[str, Dict[str, Any]])
async def get_annotations_batch(
    request: AnnotationBatchRequest,
    session: SessionDep
):
    """Get annotations for multiple genes in batch"""
    results = {}
    
    for gene_symbol in request.gene_symbols:
        gene = await crud.gene.get_by_symbol(session, gene_symbol)
        if gene:
            annotations = await crud.gene_annotation.get_by_gene(
                session,
                gene_id=gene.id,
                sources=request.sources,
                latest_only=True
            )
            results[gene_symbol] = annotations
        else:
            results[gene_symbol] = None
    
    return results

@router.get("/summary", response_model=Dict[str, Any])
async def get_annotation_summary(
    session: SessionDep,
    include_stats: bool = True
):
    """Get summary statistics for annotations"""
    summary = {
        "total_genes": await crud.gene.count(session),
        "annotated_genes": await crud.gene_annotation.count_annotated_genes(session),
        "sources": {}
    }
    
    if include_stats:
        sources = await crud.annotation_source.get_multi(session)
        for source in sources:
            summary["sources"][source.source_name] = {
                "last_update": source.last_update,
                "gene_count": await crud.gene_annotation.count_by_source(
                    session, 
                    source.source_name
                ),
                "is_active": source.is_active
            }
    
    return summary

@router.get("/search")
async def search_annotations(
    session: SessionDep,
    pli_min: Optional[float] = None,
    pli_max: Optional[float] = None,
    lof_z_min: Optional[float] = None,
    mis_z_min: Optional[float] = None,
    source: str = "gnomad",
    limit: int = 100,
    offset: int = 0
):
    """Search genes by annotation values"""
    # Build JSONB query
    filters = []
    if pli_min is not None:
        filters.append(f"(annotations->>'pli')::float >= {pli_min}")
    if pli_max is not None:
        filters.append(f"(annotations->>'pli')::float <= {pli_max}")
    if lof_z_min is not None:
        filters.append(f"(annotations->>'lof_z')::float >= {lof_z_min}")
    if mis_z_min is not None:
        filters.append(f"(annotations->>'mis_z')::float >= {mis_z_min}")
    
    results = await crud.gene_annotation.search_by_values(
        session,
        source=source,
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return results

@router.post("/refresh-materialized-view")
async def refresh_materialized_view(
    session: SessionDep,
    current_user: CurrentUser
):
    """Refresh the materialized view for fast access"""
    if not current_user.is_admin:
        raise HTTPException(403, "Admin access required")
    
    await session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary")
    await session.commit()
    
    return {"status": "success", "message": "Materialized view refreshed"}
```

### Update Pipeline Integration

```python
# backend/app/pipeline/annotation_pipeline.py

from typing import List, Dict, Any
import asyncio
from app.pipeline.sources.annotations import (
    HGNCAnnotationSource,
    GnomADAnnotationSource
)

class AnnotationPipeline:
    """Main pipeline for updating gene annotations"""
    
    def __init__(self, db_session):
        self.db_session = db_session
        self.sources = {
            "hgnc": HGNCAnnotationSource(db_session=db_session),
            "gnomad": GnomADAnnotationSource(db_session=db_session)
        }
    
    async def update_all(self, gene_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """Update annotations from all sources"""
        results = {}
        
        # Update in sequence (HGNC first as gnomAD depends on it)
        for source_name, source in self.sources.items():
            logger.info(f"Updating {source_name} annotations")
            stats = await source.update_annotations(gene_ids)
            results[source_name] = stats
        
        # Refresh materialized view
        await self.refresh_summary_view()
        
        return results
    
    async def update_source(
        self, 
        source_name: str, 
        gene_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Update annotations from specific source"""
        if source_name not in self.sources:
            raise ValueError(f"Unknown source: {source_name}")
        
        source = self.sources[source_name]
        return await source.update_annotations(gene_ids)
    
    async def refresh_summary_view(self):
        """Refresh materialized view for fast access"""
        await self.db_session.execute(
            "REFRESH MATERIALIZED VIEW CONCURRENTLY gene_annotations_summary"
        )
        await self.db_session.commit()
```

### Scheduled Updates

```python
# backend/app/tasks/annotation_tasks.py

from celery import Celery
from app.pipeline.annotation_pipeline import AnnotationPipeline

celery_app = Celery("kidney-genetics")

@celery_app.task
def update_hgnc_annotations():
    """Weekly HGNC update task"""
    async def run():
        async with get_db_session() as session:
            pipeline = AnnotationPipeline(session)
            return await pipeline.update_source("hgnc")
    
    return asyncio.run(run())

@celery_app.task
def update_gnomad_annotations():
    """Monthly gnomAD update task"""
    async def run():
        async with get_db_session() as session:
            pipeline = AnnotationPipeline(session)
            return await pipeline.update_source("gnomad")
    
    return asyncio.run(run())

# Schedule with celery beat
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'update-hgnc-weekly': {
        'task': 'app.tasks.annotation_tasks.update_hgnc_annotations',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # Monday 2 AM
    },
    'update-gnomad-monthly': {
        'task': 'app.tasks.annotation_tasks.update_gnomad_annotations',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),  # 1st of month, 3 AM
    },
}
```

## Implementation Steps

### Phase 1: Database Schema (Week 1)
1. Create migration for new annotation tables
2. Add relationships to existing Gene model
3. Create materialized view for fast access
4. Add necessary indexes

### Phase 2: HGNC Integration (Week 1)
1. Implement HGNCAnnotationSource class
2. Add MANE Select parsing
3. Test with existing HGNC client
4. Create update pipeline

### Phase 3: gnomAD Integration (Week 2)
1. Implement GnomADAnnotationSource class
2. Choose between API vs file download approach
3. Handle transcript mapping via MANE Select
4. Test constraint score retrieval

### Phase 4: API Endpoints (Week 2)
1. Implement CRUD operations for annotations
2. Add batch retrieval endpoints
3. Create search/filter endpoints
4. Add admin update triggers

### Phase 5: Optimization (Week 3)
1. Implement caching strategies
2. Optimize batch processing
3. Add progress tracking for updates
4. Performance testing

### Phase 6: Frontend Integration (Week 3)
1. Add annotation display components
2. Create filter UI for constraint scores
3. Add annotation source indicators
4. Implement update status display

## Migration Strategy

```sql
-- Migration: Add annotation tables
BEGIN;

-- Create annotation tables
CREATE TABLE gene_annotations (...);
CREATE TABLE annotation_sources (...);
CREATE TABLE annotation_history (...);

-- Migrate existing constraint_scores from gene_curations
INSERT INTO gene_annotations (gene_id, source, annotations, created_at)
SELECT 
    gc.gene_id,
    'gnomad' as source,
    gc.constraint_scores as annotations,
    gc.updated_at
FROM gene_curations gc
WHERE gc.constraint_scores IS NOT NULL;

-- Create materialized view
CREATE MATERIALIZED VIEW gene_annotations_summary AS ...;

-- Add initial sources
INSERT INTO annotation_sources (source_name, display_name, description, update_frequency)
VALUES 
    ('hgnc', 'HGNC', 'HUGO Gene Nomenclature Committee', 'weekly'),
    ('gnomad', 'gnomAD', 'Genome Aggregation Database', 'monthly');

COMMIT;
```

## Testing Strategy

### Unit Tests
- Test annotation source classes
- Test data parsing/transformation
- Test cache behavior

### Integration Tests
- Test API endpoints
- Test database operations
- Test update pipeline

### Performance Tests
- Batch processing performance
- Query performance with indexes
- Materialized view refresh time

## Monitoring & Maintenance

### Metrics to Track
- Annotation coverage (% genes with annotations)
- Update success/failure rates
- API response times
- Cache hit rates

### Alerts
- Failed update jobs
- Stale data (>30 days without update)
- API errors
- Performance degradation

## Future Extensions

### Additional Sources (Priority Order)
1. **ClinVar** - Pathogenic variant counts
2. **GTEx** - Tissue expression data
3. **STRING** - Protein interactions
4. **UniProt** - Protein function
5. **Decipher** - Developmental disorders
6. **COSMIC** - Cancer mutations
7. **dbNSFP** - Functional predictions

### Advanced Features
1. **Annotation Versioning** - Track changes over time
2. **Custom Annotations** - User-defined annotations
3. **Annotation Export** - Download in various formats
4. **GraphQL API** - Flexible querying
5. **Real-time Updates** - WebSocket notifications

## Success Criteria

1. **Data Completeness**: >95% of genes have HGNC and gnomAD annotations
2. **Performance**: <100ms response time for annotation queries
3. **Reliability**: >99% update success rate
4. **Extensibility**: New source added in <1 day of development
5. **Maintainability**: Clear documentation and test coverage >80%

## Risk Mitigation

### API Rate Limits
- Implement exponential backoff
- Use caching aggressively
- Consider local data downloads

### Data Quality
- Validate all incoming data
- Log transformation errors
- Maintain data lineage

### Performance
- Use materialized views
- Implement pagination
- Add database indexes

### Availability
- Retry failed updates
- Fallback to cached data
- Monitor source availability