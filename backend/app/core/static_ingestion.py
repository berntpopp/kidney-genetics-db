"""
Static content ingestion processor with batch normalization and chunked processing
"""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from collections import defaultdict
from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.gene_normalizer import normalize_genes_batch_async
from app.models.gene import GeneEvidence
from app.models.gene_staging import GeneNormalizationStaging
from app.models.static_ingestion import (
    StaticEvidenceUpload,
    StaticSource,
)

logger = logging.getLogger(__name__)


class StaticContentProcessor:
    """Production processor with batch normalization and chunked processing"""

    def __init__(self, db: Session):
        self.db = db
        self.chunk_size = 1000  # Process 1000 rows at a time
        self.normalization_batch_size = 100  # API rate limit safe
        self.rate_limit_delay = 0.1  # 100ms between batches

    async def process_upload(
        self,
        file: UploadFile,
        source_id: int,
        evidence_name: str,
        dry_run: bool = False
    ) -> dict[str, Any]:
        """
        Main entry point with intelligent file handling.
        Handles scraper JSON, manual CSV/TSV/Excel uploads.
        """

        # Stream to temp file while calculating hash
        file_size = 0
        hasher = hashlib.sha256()

        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as temp_file:
            temp_file_path = temp_file.name

            # Stream in 1MB chunks
            chunk_size = 1024 * 1024
            while chunk := await file.read(chunk_size):
                hasher.update(chunk)
                temp_file.write(chunk)
                file_size += len(chunk)

        file_hash = hasher.hexdigest()

        try:
            # Begin transaction
            if not dry_run:
                # Check for duplicate
                existing = self._check_duplicate(source_id, file_hash)
                if existing:
                    logger.info(f"Duplicate upload detected: {file_hash}")
                    return {
                        "status": "duplicate",
                        "upload_id": existing.id,
                        "message": f"This file was already processed on {existing.created_at}"
                    }

                # Create upload record
                upload = StaticEvidenceUpload(
                    source_id=source_id,
                    evidence_name=evidence_name,
                    file_hash=file_hash,
                    original_filename=file.filename,
                    content_type=file.content_type,
                    upload_status='processing',
                    uploaded_by=None  # Will be set by API endpoint
                )
                self.db.add(upload)
                self.db.flush()
                upload_id = upload.id
            else:
                upload_id = None

            # Detect format
            file_type = self._detect_format(file.filename, file.content_type)

            # Route based on size
            if file_size > 10 * 1024 * 1024:  # >10MB
                logger.info(f"Large file ({file_size:,} bytes), using chunked processing")
                result = await self._process_large_file_chunked(
                    temp_file_path, file_type, file_hash,
                    source_id, evidence_name, file.filename, dry_run
                )
            else:
                logger.info(f"Small file ({file_size:,} bytes), using memory processing")
                with open(temp_file_path, 'rb') as f:
                    content = f.read()
                result = await self._process_small_file_batch(
                    content, file_type, file_hash,
                    source_id, evidence_name, file.filename, dry_run
                )

            # Update upload record
            if not dry_run and upload_id:
                upload = self.db.query(StaticEvidenceUpload).get(upload_id)
                upload.upload_status = 'completed' if result['status'] == 'success' else 'failed'
                upload.processing_log = result.get('stats', {})
                upload.gene_count = result.get('stats', {}).get('total_genes', 0)
                upload.genes_normalized = result.get('stats', {}).get('normalized', 0)
                upload.genes_failed = result.get('stats', {}).get('failed', 0)
                upload.genes_staged = result.get('stats', {}).get('staged', 0)
                upload.processed_at = datetime.utcnow()

                # Extract provider metadata if available
                if 'provider_metadata' in result:
                    upload.upload_metadata['provider'] = result['provider_metadata']

                self.db.commit()
                result['upload_id'] = upload_id

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            if not dry_run:
                self.db.rollback()
                if upload_id:
                    # Mark upload as failed
                    upload = self.db.query(StaticEvidenceUpload).get(upload_id)
                    if upload:
                        upload.upload_status = 'failed'
                        upload.processing_log = {'error': str(e)}
                        self.db.commit()
            raise

        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    def _parse_file_content(self, content: bytes, file_type: str) -> tuple[list[dict], dict]:
        """
        Parse file content and extract metadata.
        Returns (genes_data, metadata)
        """
        import io

        metadata = {}

        if file_type == 'json':
            data = json.loads(content)

            # Handle scraper output format
            if isinstance(data, dict):
                # Extract provider metadata from scraper output
                if 'provider_id' in data:
                    metadata['provider'] = {
                        'id': data.get('provider_id'),
                        'name': data.get('provider_name'),
                        'type': data.get('provider_type'),
                        'url': data.get('main_url'),
                        'scraped_at': data.get('scraped_at')
                    }

                # Look for gene array in various locations
                for key in ['genes', 'data', 'results', 'items', 'gene_list']:
                    if key in data and isinstance(data[key], list):
                        return data[key], metadata

                # Single gene object
                if any(k in data for k in ['symbol', 'gene', 'gene_symbol']):
                    return [data], metadata

                raise ValueError(f"Cannot find gene data in JSON structure. Keys found: {list(data.keys())}")

            elif isinstance(data, list):
                return data, metadata
            else:
                raise ValueError(f"Invalid JSON structure: expected dict or list, got {type(data)}")

        elif file_type == 'csv':
            df = pd.read_csv(io.BytesIO(content))
            return df.to_dict('records'), metadata

        elif file_type == 'tsv':
            df = pd.read_csv(io.BytesIO(content), sep='\t')
            return df.to_dict('records'), metadata

        elif file_type == 'excel':
            df = pd.read_excel(io.BytesIO(content))
            return df.to_dict('records'), metadata

        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def _batch_normalize_all_symbols(
        self,
        symbols: list[str],
        source_id: int
    ) -> dict[str, dict]:
        """
        Normalize symbols with rate limiting to prevent API overload.
        """
        normalization_map = {}

        # Process in chunks to respect API rate limits
        for i in range(0, len(symbols), self.normalization_batch_size):
            chunk = symbols[i:i + self.normalization_batch_size]

            logger.info(f"Normalizing batch {i//self.normalization_batch_size + 1}, "
                       f"symbols {i+1}-{min(i+len(chunk), len(symbols))} of {len(symbols)}")

            # Call batch normalization
            batch_results = await normalize_genes_batch_async(
                db=self.db,
                gene_texts=chunk,
                source_name=f"StaticUpload_{source_id}"
            )
            
            logger.info(f"  Batch returned {len(batch_results)} results")
            if len(batch_results) != len(chunk):
                logger.warning(f"  ⚠️ Mismatch: sent {len(chunk)} symbols, got {len(batch_results)} results")
                missing = set(chunk) - set(batch_results.keys())
                if missing:
                    logger.warning(f"  Missing symbols: {list(missing)[:5]}...")

            normalization_map.update(batch_results)

            # Rate limit between batches
            if i + self.normalization_batch_size < len(symbols):
                await asyncio.sleep(self.rate_limit_delay)

        return normalization_map

    def _batch_lookup_or_create_genes(
        self,
        symbol_to_entries: dict[str, list],
        normalization_map: dict[str, dict]
    ) -> dict[str, int]:
        """
        Batch lookup or create genes to avoid N+1 queries.
        Returns a map of approved_symbol -> gene_id.
        """
        # Collect all genes that need lookup
        genes_to_lookup = []
        for symbol in symbol_to_entries.keys():
            result = normalization_map.get(symbol, {"status": "failed"})
            if result['status'] == 'normalized' and not result.get('gene_id'):
                approved_symbol = result.get('approved_symbol')
                if approved_symbol:
                    genes_to_lookup.append((symbol, approved_symbol, result.get('hgnc_id')))

        # Batch lookup all genes at once
        gene_id_map = {}
        if genes_to_lookup:
            from app.models import Gene

            # Get all existing genes in one query - check both symbol and HGNC ID
            approved_symbols = [g[1] for g in genes_to_lookup]
            hgnc_ids = [g[2] for g in genes_to_lookup if g[2]]

            # Query by both approved_symbol and hgnc_id
            from sqlalchemy import or_
            existing_genes = self.db.query(Gene).filter(
                or_(
                    Gene.approved_symbol.in_(approved_symbols),
                    Gene.hgnc_id.in_(hgnc_ids) if hgnc_ids else False
                )
            ).all()

            # Map both by symbol and HGNC ID
            hgnc_to_gene = {}
            for gene in existing_genes:
                gene_id_map[gene.approved_symbol] = gene.id
                if gene.hgnc_id:
                    hgnc_to_gene[gene.hgnc_id] = gene

            # Create missing genes in batch
            genes_to_create = []
            for _symbol, approved_symbol, hgnc_id in genes_to_lookup:
                # Check if gene exists by symbol or HGNC ID
                if approved_symbol not in gene_id_map:
                    if hgnc_id and hgnc_id in hgnc_to_gene:
                        # Gene exists with this HGNC ID but different symbol
                        # Use the existing gene
                        gene_id_map[approved_symbol] = hgnc_to_gene[hgnc_id].id
                    elif hgnc_id:
                        # Gene doesn't exist, create it
                        genes_to_create.append(Gene(
                            approved_symbol=approved_symbol,
                            hgnc_id=hgnc_id
                        ))

            if genes_to_create:
                # Add genes one by one to avoid session issues
                for gene in genes_to_create:
                    self.db.add(gene)
                self.db.flush()
                # Now get IDs
                for gene in genes_to_create:
                    gene_id_map[gene.approved_symbol] = gene.id

        return gene_id_map

    async def _process_small_file_batch(
        self,
        content: bytes,
        file_type: str,
        file_hash: str,
        source_id: int,
        evidence_name: str,
        filename: str,
        dry_run: bool
    ) -> dict[str, Any]:
        """Process small files with batch normalization."""

        # Parse content and extract metadata
        genes_data, file_metadata = self._parse_file_content(content, file_type)
        
        logger.info(f"📊 Parsed file: got {len(genes_data) if genes_data else 0} gene entries")
        if genes_data and len(genes_data) > 0:
            logger.info(f"  First entry keys: {list(genes_data[0].keys()) if isinstance(genes_data[0], dict) else 'Not a dict'}")
            logger.info(f"  First entry: {genes_data[0]}")

        if not genes_data:
            return {
                "status": "error",
                "message": "No gene data found in file"
            }

        # Extract unique symbols and map to entries
        symbol_to_entries = defaultdict(list)
        for i, entry in enumerate(genes_data):
            symbol = self._extract_gene_symbol(entry)
            if symbol:
                symbol_to_entries[symbol].append((str(i), entry))
            elif i < 5:  # Log first few failures
                logger.warning(f"  Could not extract symbol from entry {i}: {entry}")

        logger.info(f"📝 Extracted {len(symbol_to_entries)} unique symbols from {len(genes_data)} entries")
        if symbol_to_entries:
            symbols_list = list(symbol_to_entries.keys())[:10]  # First 10
            logger.info(f"  Sample symbols: {symbols_list}")
            if 'PKD1' in symbol_to_entries:
                logger.info(f"  ✅ PKD1 found in extracted symbols")
            else:
                logger.warning(f"  ❌ PKD1 NOT found in extracted symbols")

        if not symbol_to_entries:
            return {
                "status": "error",
                "message": "No valid gene symbols found"
            }

        # Batch normalize all unique symbols
        unique_symbols = list(symbol_to_entries.keys())
        logger.info(f"Found {len(unique_symbols):,} unique symbols from {len(genes_data):,} entries")
        logger.info(f"🔄 Processing upload for source_id={source_id}, evidence_name={evidence_name}, dry_run={dry_run}")

        normalization_map = await self._batch_normalize_all_symbols(
            unique_symbols, source_id
        )
        
        logger.info(f"🔬 Normalization results: {len(normalization_map)} symbols processed")
        normalized_count = sum(1 for r in normalization_map.values() if r.get('status') == 'normalized')
        staged_count = sum(1 for r in normalization_map.values() if r.get('status') == 'staged')
        logger.info(f"  Normalized: {normalized_count}, Staged: {staged_count}")
        
        if 'PKD1' in normalization_map:
            logger.info(f"  PKD1 normalization result: {normalization_map['PKD1']}")

        # Process results
        total_stats = {
            "total_genes": len(genes_data),
            "normalized": 0,
            "staged": 0,
            "failed": 0
        }

        evidence_batch = []
        staging_batch = []

        # Use internal naming pattern: static_{source_id}
        # This ensures uniqueness and follows the same pattern as other sources
        source_name = f"static_{source_id}"
        logger.info(f"Using internal source name: {source_name} for source_id: {source_id}")

        # Batch lookup/create all genes to avoid N+1 queries
        gene_id_map = self._batch_lookup_or_create_genes(symbol_to_entries, normalization_map)

        for symbol, entries in symbol_to_entries.items():
            result = normalization_map.get(symbol, {"status": "failed"})

            for _unique_key, entry in entries:
                if result['status'] == 'normalized':
                    # Use gene_id from normalizer if available, otherwise look it up from batch map
                    gene_id = result.get('gene_id')

                    if not gene_id:
                        approved_symbol = result.get('approved_symbol')
                        if approved_symbol:
                            gene_id = gene_id_map.get(approved_symbol)

                    if gene_id:
                        total_stats["normalized"] += 1

                        if not dry_run:
                            # Build evidence data preserving all fields
                            evidence_data = {
                                "original_symbol": symbol,
                                "confidence": entry.get("confidence", "medium"),
                                "provider": evidence_name,  # Store provider name
                            }

                            # Preserve panels from scraper data
                            if "panels" in entry:
                                evidence_data["panels"] = entry["panels"]
                                logger.debug(f"Gene {symbol} (ID: {result.get('gene_id', 'N/A')}): panels={entry['panels']}, provider={evidence_name}, source={source_name}")

                            # Preserve occurrence count
                            if "occurrence_count" in entry:
                                evidence_data["occurrence_count"] = entry["occurrence_count"]

                            # Store all other metadata
                            evidence_data["metadata"] = {
                                k: v for k, v in entry.items()
                                if k not in ['symbol', 'gene_symbol', 'gene', 'panels',
                                           'confidence', 'occurrence_count']
                            }

                            evidence_batch.append({
                                "gene_id": gene_id,
                                "source_name": source_name,
                                "source_detail": evidence_name,
                                "evidence_data": evidence_data
                            })

                elif result['status'] == 'staged':
                    total_stats["staged"] += 1

                    if not dry_run:
                        staging_batch.append({
                            "original_text": symbol,
                            "source_name": source_name,
                            "original_data": entry,
                            "normalization_log": result.get('log', {}),
                            "priority_score": self._calculate_priority(entry)
                        })
                else:
                    total_stats["failed"] += 1

        # Bulk insert with transaction
        if not dry_run:
            try:
                if evidence_batch:
                    # Fetch source info for scoring
                    source = self.db.query(StaticSource).filter(StaticSource.id == source_id).first()
                    if source:
                        source_dict = {
                            "id": source.id,
                            "scoring_metadata": source.scoring_metadata
                        }
                        self._bulk_insert_evidence(evidence_batch, source_dict)
                if staging_batch:
                    self._bulk_insert_staging(staging_batch)
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        return {
            "status": "success",
            "stats": total_stats,
            "provider_metadata": file_metadata.get('provider')
        }

    async def _process_large_file_chunked(
        self,
        file_path: str,
        file_type: str,
        file_hash: str,
        source_id: int,
        evidence_name: str,
        filename: str,
        dry_run: bool
    ) -> dict[str, Any]:
        """
        Process large files with two-pass approach:
        1. Collect all unique symbols
        2. Batch normalize with rate limiting
        3. Process and insert in chunks
        """

        if file_type not in ['csv', 'tsv', 'excel']:
            # JSON must fit in memory for parsing
            with open(file_path, 'rb') as f:
                content = f.read()
            return await self._process_small_file_batch(
                content, 'json', file_hash,
                source_id, evidence_name, filename, dry_run
            )

        # Pass 1: Collect unique symbols
        logger.info("Pass 1: Collecting unique gene symbols")
        unique_symbols = set()
        symbol_to_entries = defaultdict(list)

        # Configure pandas reader
        if file_type == 'excel':
            reader_func = pd.read_excel
            reader_kwargs = {'chunksize': self.chunk_size}
        else:
            reader_func = pd.read_csv
            sep = '\t' if file_type == 'tsv' else ','
            reader_kwargs = {'sep': sep, 'chunksize': self.chunk_size}

        # Collect symbols
        row_count = 0
        with reader_func(file_path, **reader_kwargs) as reader:
            for chunk_num, chunk in enumerate(reader):
                genes_data = chunk.to_dict('records')

                for i, entry in enumerate(genes_data):
                    symbol = self._extract_gene_symbol(entry)
                    if symbol:
                        unique_key = f"{row_count + i}"
                        unique_symbols.add(symbol)
                        symbol_to_entries[symbol].append((unique_key, entry))

                row_count += len(genes_data)

                if chunk_num % 10 == 0:
                    logger.info(f"Scanned {row_count:,} rows, found {len(unique_symbols):,} unique symbols")

        logger.info(f"Found {len(unique_symbols):,} unique symbols in {row_count:,} rows")

        # Pass 2: Batch normalize with rate limiting
        if unique_symbols:
            normalization_map = await self._batch_normalize_all_symbols(
                list(unique_symbols), source_id
            )
        else:
            normalization_map = {}

        # Pass 3: Process results and build insert batches
        logger.info("Pass 3: Processing normalized results")

        total_stats = {
            "total_genes": row_count,
            "normalized": 0,
            "staged": 0,
            "failed": 0
        }

        evidence_batch = []
        staging_batch = []

        # Use internal naming pattern: static_{source_id}
        source_name = f"static_{source_id}"
        logger.info(f"Using internal source name: {source_name} for source_id: {source_id}")

        # Batch lookup/create all genes to avoid N+1 queries
        gene_id_map = self._batch_lookup_or_create_genes(symbol_to_entries, normalization_map)

        # Process normalization results
        for symbol, entries in symbol_to_entries.items():
            result = normalization_map.get(symbol, {"status": "failed"})

            for _unique_key, entry in entries:
                if result['status'] == 'normalized':
                    # Use gene_id from normalizer if available, otherwise look it up from batch map
                    gene_id = result.get('gene_id')

                    if not gene_id:
                        approved_symbol = result.get('approved_symbol')
                        if approved_symbol:
                            gene_id = gene_id_map.get(approved_symbol)

                    if gene_id:
                        total_stats["normalized"] += 1

                        if not dry_run:
                            evidence_data = {
                                "original_symbol": symbol,
                                "confidence": entry.get("confidence", "medium"),
                                "metadata": {k: v for k, v in entry.items()
                                           if k not in ['symbol', 'gene_symbol', 'gene', 'confidence']}
                            }

                            evidence_batch.append({
                                "gene_id": gene_id,
                                "source_name": source_name,
                                "source_detail": evidence_name,
                                "evidence_data": evidence_data
                            })

                elif result['status'] == 'staged':
                    total_stats["staged"] += 1

                    if not dry_run:
                        staging_batch.append({
                            "original_text": symbol,
                            "source_name": source_name,
                            "original_data": entry,
                            "normalization_log": result.get('log', {}),
                            "priority_score": self._calculate_priority(entry)
                        })
                else:
                    total_stats["failed"] += 1

                # Periodic batch insert with transaction
                if len(evidence_batch) >= 500:
                    try:
                        # Fetch source info for scoring
                        source = self.db.query(StaticSource).filter(StaticSource.id == source_id).first()
                        if source:
                            source_dict = {
                                "id": source.id,
                                "scoring_metadata": source.scoring_metadata
                            }
                            self._bulk_insert_evidence(evidence_batch, source_dict)
                        self.db.commit()
                        evidence_batch = []
                        logger.info(f"Inserted batch, progress: {total_stats['normalized']:,} normalized")
                    except Exception:
                        self.db.rollback()
                        raise

                if len(staging_batch) >= 500:
                    try:
                        self._bulk_insert_staging(staging_batch)
                        self.db.commit()
                        staging_batch = []
                    except Exception:
                        self.db.rollback()
                        raise

        # Final inserts
        if not dry_run:
            try:
                if evidence_batch:
                    # Fetch source info for scoring
                    source = self.db.query(StaticSource).filter(StaticSource.id == source_id).first()
                    if source:
                        source_dict = {
                            "id": source.id,
                            "scoring_metadata": source.scoring_metadata
                        }
                        self._bulk_insert_evidence(evidence_batch, source_dict)
                if staging_batch:
                    self._bulk_insert_staging(staging_batch)
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        logger.info(f"Upload complete: {total_stats}")

        return {
            "status": "success",
            "stats": total_stats
        }

    def _batch_get_or_create_genes(self, normalized_results: dict[str, dict]) -> dict[str, int]:
        """Batch fetch or create genes, returning symbol->gene_id mapping"""
        from sqlalchemy import or_

        from app.models import Gene

        gene_mapping = {}

        # Collect all unique symbols and HGNC IDs
        symbols_to_fetch = set()
        hgnc_ids_to_fetch = set()

        for _symbol, result in normalized_results.items():
            if result['status'] == 'normalized' and not result.get('gene_id'):
                if result.get('approved_symbol'):
                    symbols_to_fetch.add(result['approved_symbol'])
                if result.get('hgnc_id'):
                    hgnc_ids_to_fetch.add(result['hgnc_id'])

        if not symbols_to_fetch and not hgnc_ids_to_fetch:
            # All genes already have IDs
            for symbol, result in normalized_results.items():
                if result.get('gene_id'):
                    gene_mapping[symbol] = result['gene_id']
            return gene_mapping

        # Batch fetch existing genes
        conditions = []
        if symbols_to_fetch:
            conditions.append(Gene.approved_symbol.in_(symbols_to_fetch))
        if hgnc_ids_to_fetch:
            conditions.append(Gene.hgnc_id.in_(hgnc_ids_to_fetch))

        existing_genes = self.db.query(Gene).filter(or_(*conditions)).all()

        # Map existing genes
        symbol_to_gene = {g.approved_symbol: g for g in existing_genes}
        hgnc_to_gene = {g.hgnc_id: g for g in existing_genes if g.hgnc_id}

        # Process results and create missing genes
        genes_to_create = []
        for symbol, result in normalized_results.items():
            if result['status'] == 'normalized':
                if result.get('gene_id'):
                    gene_mapping[symbol] = result['gene_id']
                else:
                    approved_symbol = result.get('approved_symbol')
                    hgnc_id = result.get('hgnc_id')

                    gene = symbol_to_gene.get(approved_symbol) or hgnc_to_gene.get(hgnc_id)

                    if gene:
                        gene_mapping[symbol] = gene.id
                    elif approved_symbol and hgnc_id:
                        # Create new gene
                        new_gene = Gene(
                            approved_symbol=approved_symbol,
                            hgnc_id=hgnc_id
                        )
                        genes_to_create.append(new_gene)
                        self.db.add(new_gene)

        # Flush to get IDs for new genes
        if genes_to_create:
            self.db.flush()
            for gene in genes_to_create:
                gene_mapping[gene.approved_symbol] = gene.id

        return gene_mapping

    def _extract_gene_symbol(self, entry: dict) -> str | None:
        """Extract and normalize gene symbol from various field names"""
        # Try common field names (order matters - prefer specific fields)
        field_names = ['symbol', 'gene_symbol', 'gene', 'Gene', 'GENE',
                      'gene_name', 'geneName', 'SYMBOL', 'Symbol']

        for field in field_names:
            if field in entry and entry[field]:
                value = str(entry[field]).strip().upper()
                # Skip invalid values
                if value and value not in ['NA', 'NULL', 'NONE', '', 'N/A', 'UNKNOWN']:
                    return value
        return None

    def _calculate_priority(self, entry: dict) -> int:
        """Calculate priority for manual review"""
        score = 0

        # Higher priority for high confidence
        confidence = entry.get("confidence", "").lower()
        if confidence == "high":
            score += 10
        elif confidence == "medium":
            score += 5

        # Higher priority if has HGNC ID
        if entry.get("hgnc_id"):
            score += 15

        # Higher priority if appears in multiple panels
        if "panels" in entry and isinstance(entry["panels"], list):
            score += min(len(entry["panels"]) * 2, 10)

        # Higher priority for entries with more metadata
        if len(entry) > 3:
            score += 5

        return score

    def _calculate_normalized_score(self, evidence_data: dict, source_metadata: dict) -> float:
        """Calculate normalized score based on source metadata"""
        scoring_metadata = source_metadata.get("scoring_metadata", {})
        scoring_type = scoring_metadata.get("type", "count")
        weight = scoring_metadata.get("weight", 1.0)

        if scoring_type == "count":
            # Count-based scoring (e.g., count of panels)
            field = scoring_metadata.get("field", "panels")
            if field in evidence_data and isinstance(evidence_data[field], list):
                count = len(evidence_data[field])
                # Normalize to 0-1 scale with diminishing returns
                normalized = min(1.0, count / 10.0)  # Assume 10+ is maximum
            else:
                normalized = 0.5  # Default for missing data
        elif scoring_type == "classification":
            # Classification-based scoring
            weight_map = scoring_metadata.get("weight_map", {})
            classification = evidence_data.get("classification", "unknown")
            normalized = weight_map.get(classification, 0.5)
        elif scoring_type == "fixed":
            # Fixed score
            normalized = scoring_metadata.get("score", 1.0)
        else:
            normalized = 0.5  # Default fallback

        return float(normalized * weight)

    def _merge_evidence_data(self, existing_data: dict, new_data: dict) -> dict:
        """Merge new evidence data with existing data"""
        merged = existing_data.copy() if existing_data else {}

        # Merge panels - preserve provider information
        if "panels" in new_data:
            # Migrate old format to new provider-based format
            if "providers" not in merged:
                merged["providers"] = {}

                # Convert existing panels to provider format if needed
                if "panels" in merged:
                    # This is legacy data, we'll keep it for now
                    pass

            # Add new panels under their provider
            # The source_detail should contain the provider name
            provider_name = new_data.get("provider", "Unknown")
            if provider_name not in merged["providers"]:
                merged["providers"][provider_name] = []

            # Add panels for this provider
            for panel in new_data.get("panels", []):
                panel_name = panel.get('name', panel) if isinstance(panel, dict) else panel
                if panel_name and panel_name not in merged["providers"][provider_name]:
                    merged["providers"][provider_name].append(panel_name)

            # Also maintain flat panels list for backward compatibility
            if "panels" not in merged:
                merged["panels"] = []

            existing_panel_names = set()
            for panel in merged["panels"]:
                if isinstance(panel, dict):
                    existing_panel_names.add(panel.get('name', ''))
                else:
                    existing_panel_names.add(str(panel))

            for panel in new_data.get("panels", []):
                panel_obj = {"name": panel.get('name', panel) if isinstance(panel, dict) else panel}
                if panel_obj["name"] and panel_obj["name"] not in existing_panel_names:
                    merged["panels"].append(panel_obj)
                    existing_panel_names.add(panel_obj["name"])

        # Update confidence (use highest)
        if "confidence" in new_data:
            existing_conf = merged.get("confidence", "low")
            new_conf = new_data["confidence"]
            conf_order = {"low": 0, "medium": 1, "high": 2}
            if conf_order.get(new_conf, 0) > conf_order.get(existing_conf, 0):
                merged["confidence"] = new_conf

        # Update other fields
        for key, value in new_data.items():
            if key not in ["panels", "confidence"]:
                merged[key] = value

        return merged

    def _bulk_insert_evidence(self, evidence_batch: list[dict], source: dict):
        """Insert or update evidence records - keep separate entries per provider"""
        if not evidence_batch:
            return

        inserted = 0
        updated = 0

        for evidence_data in evidence_batch:
            # For diagnostic panels, check by gene_id AND source_detail (provider)
            # This keeps separate evidence entries per provider
            existing = self.db.query(GeneEvidence).filter(
                GeneEvidence.gene_id == evidence_data['gene_id'],
                GeneEvidence.source_name == evidence_data['source_name'],
                GeneEvidence.source_detail == evidence_data['source_detail']
            ).first()

            if existing:
                # Update existing provider's evidence
                existing.evidence_data = evidence_data['evidence_data']
                existing.updated_at = datetime.utcnow()
                updated += 1
                logger.debug(f"Updated evidence for gene {evidence_data['gene_id']}, provider: {evidence_data['source_detail']}")
            else:
                # Create new evidence entry for this provider
                new_evidence = GeneEvidence(**evidence_data)
                self.db.add(new_evidence)
                inserted += 1
                logger.debug(f"Created evidence for gene {evidence_data['gene_id']}, provider: {evidence_data['source_detail']}")

        self.db.flush()
        logger.info(f"Evidence records: {inserted} inserted, {updated} updated")

    def _bulk_insert_staging(self, staging_batch: list[dict]):
        """Efficiently insert staging records"""
        if not staging_batch:
            return

        self.db.bulk_insert_mappings(GeneNormalizationStaging, staging_batch)
        self.db.flush()
        logger.info(f"Bulk inserted {len(staging_batch)} staging records")

    def _check_duplicate(self, source_id: int, file_hash: str):
        """Check for duplicate upload"""
        return self.db.query(StaticEvidenceUpload).filter(
            StaticEvidenceUpload.source_id == source_id,
            StaticEvidenceUpload.file_hash == file_hash,
            StaticEvidenceUpload.upload_status != 'superseded'
        ).first()

    def _detect_format(self, filename: str, content_type: str) -> str:
        """Detect file format from filename and content type"""
        filename_lower = filename.lower()

        if filename_lower.endswith('.json'):
            return 'json'
        elif filename_lower.endswith('.csv'):
            return 'csv'
        elif filename_lower.endswith(('.tsv', '.txt', '.tab')):
            return 'tsv'
        elif filename_lower.endswith(('.xlsx', '.xls')):
            return 'excel'
        elif content_type:
            if 'json' in content_type:
                return 'json'
            elif 'csv' in content_type:
                return 'csv'
            elif 'tab-separated' in content_type or 'tsv' in content_type:
                return 'tsv'
            elif 'excel' in content_type or 'spreadsheet' in content_type:
                return 'excel'

        raise ValueError(f"Cannot determine format for {filename} (content-type: {content_type})")

