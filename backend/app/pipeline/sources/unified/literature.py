"""
Unified Literature data source implementation.

This module provides a hybrid source that accepts file uploads for literature
references and properly aggregates evidence across multiple sources.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from typing import TYPE_CHECKING, Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache_service import CacheService
from app.core.cached_http_client import CachedHttpClient
from app.models.gene import Gene, GeneEvidence
from app.pipeline.sources.unified.base import UnifiedDataSource

if TYPE_CHECKING:
    from app.core.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class LiteratureSource(UnifiedDataSource):
    """
    Hybrid data source for literature references.
    
    This source accepts file uploads containing literature/publication data
    and properly aggregates references by gene, deduplicating by PMID.
    
    Key features:
    - Supports multiple file formats (JSON, CSV, Excel)
    - Deduplicates references by PMID
    - Merges evidence on re-upload
    - Tracks multiple data sources
    """

    @property
    def source_name(self) -> str:
        return "Literature"

    @property
    def namespace(self) -> str:
        return "literature"

    def __init__(
        self,
        cache_service: CacheService | None = None,
        http_client: CachedHttpClient | None = None,
        db_session: Session | None = None,
        **kwargs,
    ):
        """Initialize literature source."""
        super().__init__(cache_service, http_client, db_session, **kwargs)
        logger.info("LiteratureSource initialized")

    def _get_default_ttl(self) -> int:
        """Get default TTL - manual uploads don't expire."""
        return 86400 * 365  # 1 year

    async def fetch_raw_data(
        self,
        file_content: bytes,
        file_type: str,
        source_name: str,
        tracker: "ProgressTracker" = None
    ) -> pd.DataFrame:
        """
        Parse uploaded literature file and return DataFrame.
        
        Args:
            file_content: Raw file bytes
            file_type: File extension (json, csv, tsv, xlsx, xls)
            source_name: Name of the literature source
            tracker: Optional progress tracker
            
        Returns:
            DataFrame with literature reference data
        """
        logger.info(f"Processing {file_type} literature file from: {source_name}")

        try:
            if file_type == 'json':
                df = self._parse_json(file_content)
            elif file_type in ['csv', 'tsv']:
                df = self._parse_csv(file_content, file_type)
            elif file_type in ['xlsx', 'xls']:
                df = self._parse_excel(file_content)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Add source metadata
            df['source'] = source_name

            logger.info(f"Parsed {len(df)} reference entries from {source_name}")
            return df

        except Exception as e:
            logger.error(f"Failed to parse literature file from {source_name}: {e}")
            raise

    def _parse_json(self, content: bytes) -> pd.DataFrame:
        """Parse JSON file format."""
        data = json.loads(content)

        # Handle different JSON structures
        if isinstance(data, dict):
            if 'references' in data:
                ref_list = data['references']
            elif 'publications' in data:
                ref_list = data['publications']
            elif 'articles' in data:
                ref_list = data['articles']
            elif 'data' in data:
                ref_list = data['data']
            else:
                # Try to find any list in the dict
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        ref_list = value
                        break
                else:
                    raise ValueError("Cannot find reference array in JSON structure")
        elif isinstance(data, list):
            ref_list = data
        else:
            raise ValueError("Invalid JSON structure for literature data")

        return pd.DataFrame(ref_list)

    def _parse_csv(self, content: bytes, file_type: str) -> pd.DataFrame:
        """Parse CSV or TSV file."""
        sep = '\t' if file_type == 'tsv' else ','
        return pd.read_csv(BytesIO(content), sep=sep)

    def _parse_excel(self, content: bytes) -> pd.DataFrame:
        """Parse Excel file."""
        return pd.read_excel(BytesIO(content))

    async def process_data(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Process DataFrame and aggregate literature references by gene.
        
        Args:
            df: DataFrame with literature reference data
            
        Returns:
            Dictionary mapping gene symbols to aggregated references
        """
        gene_data = defaultdict(lambda: {
            "references": {},  # Use dict for deduplication by PMID
            "sources": set(),
            "evidence_types": set()
        })

        for _, row in df.iterrows():
            # Extract gene symbol
            symbol = self._extract_gene_symbol(row)
            if not symbol:
                continue

            # Create reference object
            ref = self._create_reference(row)

            # Only add if has valid PMID (for deduplication)
            if ref.get("pmid"):
                pmid = str(ref["pmid"])
                # Update or add reference (latest version wins)
                gene_data[symbol]["references"][pmid] = ref

            # Track source
            if "source" in row and pd.notna(row["source"]):
                gene_data[symbol]["sources"].add(str(row["source"]))

            # Track evidence types
            if ref.get("evidence_type"):
                gene_data[symbol]["evidence_types"].add(ref["evidence_type"])

        # Convert to serializable format
        result = {}
        for symbol, data in gene_data.items():
            # Convert reference dict to list
            references = list(data["references"].values())

            result[symbol] = {
                "references": references,
                "publication_count": len(references),
                "sources": sorted(list(data["sources"])),
                "evidence_types": sorted(list(data["evidence_types"]))
            }

        logger.info(f"Processed {len(result)} genes with {sum(r['publication_count'] for r in result.values())} total references")
        return result

    def _extract_gene_symbol(self, row: pd.Series) -> str | None:
        """Extract gene symbol from various possible field names."""
        field_names = [
            'gene_symbol', 'symbol', 'gene', 'Gene', 'GENE',
            'approved_symbol', 'gene_name', 'geneName', 'SYMBOL', 'Symbol'
        ]

        for field in field_names:
            if field in row and pd.notna(row[field]):
                value = str(row[field]).strip().upper()
                # Skip invalid values
                if value and value not in ['NA', 'NULL', 'NONE', '', 'N/A', 'UNKNOWN']:
                    return value
        return None

    def _create_reference(self, row: pd.Series) -> dict[str, Any]:
        """Create a reference object from row data."""
        ref = {}

        # PMID (required for deduplication)
        if "pmid" in row and pd.notna(row["pmid"]):
            ref["pmid"] = str(row["pmid"]).strip()
        elif "PMID" in row and pd.notna(row["PMID"]):
            ref["pmid"] = str(row["PMID"]).strip()

        # Title
        if "title" in row and pd.notna(row["title"]):
            ref["title"] = str(row["title"]).strip()

        # Authors
        if "authors" in row and pd.notna(row["authors"]):
            authors = row["authors"]
            if isinstance(authors, str):
                ref["authors"] = authors
            elif isinstance(authors, list):
                ref["authors"] = "; ".join(str(a) for a in authors)

        # Year
        for field in ["year", "publication_year", "pub_year"]:
            if field in row and pd.notna(row[field]):
                try:
                    ref["year"] = int(row[field])
                    break
                except (ValueError, TypeError):
                    pass

        # Journal
        if "journal" in row and pd.notna(row["journal"]):
            ref["journal"] = str(row["journal"]).strip()

        # Evidence type
        if "evidence_type" in row and pd.notna(row["evidence_type"]):
            ref["evidence_type"] = str(row["evidence_type"]).strip()
        else:
            ref["evidence_type"] = "association"  # Default

        # DOI
        if "doi" in row and pd.notna(row["doi"]):
            ref["doi"] = str(row["doi"]).strip()

        return ref

    async def store_evidence(
        self,
        db: Session,
        gene_data: dict[str, Any],
        source_detail: str | None = None
    ) -> dict[str, Any]:
        """
        Store literature evidence with merge semantics.
        
        This method properly merges references from multiple uploads,
        deduplicating by PMID to avoid duplicate publications.
        
        Args:
            db: Database session
            gene_data: Processed gene evidence data
            source_detail: Optional source detail
            
        Returns:
            Statistics about the storage operation
        """
        if not gene_data:
            return {"merged": 0, "created": 0, "failed": 0}

        stats = {"merged": 0, "created": 0, "failed": 0}

        # Get gene IDs for all symbols
        gene_symbols = list(gene_data.keys())
        gene_map = {}

        # Batch fetch genes
        stmt = select(Gene).where(Gene.approved_symbol.in_(gene_symbols))
        genes = db.execute(stmt).scalars().all()
        gene_map = {g.approved_symbol: g.id for g in genes}

        # Get existing evidence for these genes
        gene_ids = list(gene_map.values())
        stmt = select(GeneEvidence).where(
            GeneEvidence.gene_id.in_(gene_ids),
            GeneEvidence.source_name == self.source_name
        )
        existing_evidence = db.execute(stmt).scalars().all()
        existing_map = {e.gene_id: e for e in existing_evidence}

        # Process each gene
        for symbol, data in gene_data.items():
            gene_id = gene_map.get(symbol)
            if not gene_id:
                logger.warning(f"Gene {symbol} not found in database")
                stats["failed"] += 1
                continue

            if gene_id in existing_map:
                # MERGE: Update existing evidence
                record = existing_map[gene_id]
                current_data = record.evidence_data or {}

                # Merge references by PMID (deduplication)
                current_refs = {
                    r.get("pmid", f"no_pmid_{i}"): r
                    for i, r in enumerate(current_data.get("references", []))
                }

                # Add new references (overwrites if same PMID)
                for new_ref in data["references"]:
                    pmid = new_ref.get("pmid", f"no_pmid_new_{len(current_refs)}")
                    current_refs[pmid] = new_ref

                # Merge sources
                current_sources = set(current_data.get("sources", []))
                current_sources.update(data.get("sources", []))

                # Merge evidence types
                current_types = set(current_data.get("evidence_types", []))
                current_types.update(data.get("evidence_types", []))

                # Update evidence with merged data
                all_refs = list(current_refs.values())
                record.evidence_data = {
                    "references": all_refs,
                    "publication_count": len(all_refs),
                    "sources": sorted(list(current_sources)),
                    "evidence_types": sorted(list(current_types))
                }
                record.source_detail = f"{len(all_refs)} publications"
                record.updated_at = datetime.now(timezone.utc)

                logger.debug(f"Merged literature for {symbol}: {len(all_refs)} publications from {len(current_sources)} sources")
                stats["merged"] += 1

            else:
                # CREATE: New evidence record
                record = GeneEvidence(
                    gene_id=gene_id,
                    source_name=self.source_name,
                    source_detail=f"{data['publication_count']} publications",
                    evidence_data=data,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.add(record)

                logger.debug(f"Created literature for {symbol}: {data['publication_count']} publications")
                stats["created"] += 1

        # Commit the transaction
        db.commit()

        logger.info(f"Storage complete: {stats['created']} created, {stats['merged']} merged, {stats['failed']} failed")
        return stats

    def is_kidney_related(self, record: dict[str, Any]) -> bool:
        """All manually uploaded literature is considered kidney-related."""
        return True
