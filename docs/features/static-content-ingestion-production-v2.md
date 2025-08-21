# Static Content Ingestion System - Production Implementation V2

## Executive Summary

A production-ready REST API system for ingesting static and scraped content into the kidney-genetics database. This implementation handles multiple file formats (JSON from scrapers, CSV, TSV, Excel) through a unified interface with metadata-driven scoring, batch normalization, and memory-efficient processing.

## Core Architectural Decisions

### 1. Universal File Handler
Single ingestion system handles all formats including scraper JSON outputs and manual uploads without special-case code.

### 2. Metadata-Driven Scoring
Each static source defines scoring rules through database configuration for complete flexibility.

### 3. Batch Processing with Rate Limiting
Batch normalization with HGNC API rate limiting to prevent overload.

### 4. Memory-Efficient Streaming
Large files processed in chunks with proper transaction boundaries.

### 5. Non-Breaking Integration
New scoring views separate from existing GenCC/ClinGen views to prevent regressions.

## Implementation Details

### 1. Database Models and Migration

```python
# backend/app/models/static_ingestion.py

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin

class StaticSource(Base, TimestampMixin):
    """Static evidence source configuration"""
    
    __tablename__ = "static_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    source_name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    metadata = Column(JSONB, default={})
    scoring_metadata = Column(JSONB, nullable=False, default={"type": "count", "weight": 0.5})
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(255))
    
    # Relationships
    uploads = relationship("StaticEvidenceUpload", back_populates="source", cascade="all, delete-orphan")
    audit_logs = relationship("StaticSourceAudit", back_populates="source", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<StaticSource(name='{self.source_name}', type='{self.source_type}')>"

class StaticEvidenceUpload(Base, TimestampMixin):
    """Track evidence file uploads"""
    
    __tablename__ = "static_evidence_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    original_filename = Column(String(255))
    content_type = Column(String(50))
    upload_status = Column(String(50), default="pending", index=True)
    processing_log = Column(JSONB, default={})
    gene_count = Column(Integer)
    genes_normalized = Column(Integer)
    genes_failed = Column(Integer)
    genes_staged = Column(Integer)
    metadata = Column(JSONB, default={})
    processed_at = Column(DateTime(timezone=True))
    uploaded_by = Column(String(255))
    
    # Relationships
    source = relationship("StaticSource", back_populates="uploads")
    
    def __repr__(self):
        return f"<StaticEvidenceUpload(source_id={self.source_id}, evidence='{self.evidence_name}')>"

class StaticSourceAudit(Base):
    """Audit trail for static source operations"""
    
    __tablename__ = "static_source_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("static_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey("static_evidence_uploads.id", ondelete="CASCADE"))
    action = Column(String(50), nullable=False)
    details = Column(JSONB, default={})
    performed_by = Column(String(255))
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source = relationship("StaticSource", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<StaticSourceAudit(source_id={self.source_id}, action='{self.action}')>"
```

```python
# backend/alembic/versions/xxx_add_static_ingestion_tables.py

"""Add static content ingestion tables

Revision ID: xxx
Revises: previous_migration
Create Date: 2025-01-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create static_sources table
    op.create_table('static_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('scoring_metadata', postgresql.JSONB(), 
                  server_default='{"type": "count", "weight": 0.5}', 
                  nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name'),
        sa.CheckConstraint(
            "source_type IN ('diagnostic_panel', 'manual_curation', 'literature_review', 'custom')",
            name='static_sources_type_check'
        )
    )
    
    # Create static_evidence_uploads table
    op.create_table('static_evidence_uploads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('evidence_name', sa.String(255), nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False),
        sa.Column('original_filename', sa.String(255)),
        sa.Column('content_type', sa.String(50)),
        sa.Column('upload_status', sa.String(50), server_default='pending'),
        sa.Column('processing_log', postgresql.JSONB(), server_default='{}'),
        sa.Column('gene_count', sa.Integer()),
        sa.Column('genes_normalized', sa.Integer()),
        sa.Column('genes_failed', sa.Integer()),
        sa.Column('genes_staged', sa.Integer()),
        sa.Column('metadata', postgresql.JSONB(), server_default='{}'),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('uploaded_by', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'file_hash', name='unique_upload_per_source'),
        sa.CheckConstraint(
            "upload_status IN ('pending', 'processing', 'completed', 'failed', 'superseded')",
            name='upload_status_check'
        )
    )
    
    # Create static_source_audit table
    op.create_table('static_source_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('upload_id', sa.Integer()),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('details', postgresql.JSONB(), server_default='{}'),
        sa.Column('performed_by', sa.String(255)),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['static_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['upload_id'], ['static_evidence_uploads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_static_sources_type', 'static_sources', ['source_type'])
    op.create_index('idx_static_sources_active', 'static_sources', ['is_active'])
    op.create_index('idx_uploads_source_id', 'static_evidence_uploads', ['source_id'])
    op.create_index('idx_uploads_status', 'static_evidence_uploads', ['upload_status'])
    op.create_index('idx_uploads_hash', 'static_evidence_uploads', ['file_hash'])
    op.create_index('idx_audit_source_id', 'static_source_audit', ['source_id'])
    
    # Create separate scoring views for static sources
    op.execute("""
        -- Count evidence for static sources
        CREATE VIEW static_evidence_counts AS
        SELECT 
            ge.id as evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.id as source_id,
            CASE
                WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                     AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                    jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))
                ELSE 1
            END as source_count
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)
    
    op.execute("""
        -- Scoring for static sources (separate from main evidence scoring)
        CREATE VIEW static_evidence_scores AS
        SELECT
            ge.id AS evidence_id,
            ge.gene_id,
            g.approved_symbol,
            ge.source_name,
            ss.display_name as source_display_name,
            CASE
                -- Count-based scoring
                WHEN ss.scoring_metadata->>'type' = 'count' THEN
                    CASE
                        WHEN ss.scoring_metadata->>'field' IS NOT NULL 
                             AND ge.evidence_data ? (ss.scoring_metadata->>'field') THEN
                            LEAST(
                                jsonb_array_length(ge.evidence_data -> (ss.scoring_metadata->>'field'))::float 
                                / 10.0 * COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5),
                                1.0
                            )
                        ELSE COALESCE((ss.scoring_metadata->>'weight')::numeric, 0.5)
                    END
                
                -- Classification-based scoring
                WHEN ss.scoring_metadata->>'type' = 'classification' 
                     AND ss.scoring_metadata->>'field' IS NOT NULL THEN
                    COALESCE(
                        (ss.scoring_metadata->'weight_map' ->> 
                            (ge.evidence_data->>(ss.scoring_metadata->>'field'))
                        )::numeric,
                        0.3
                    )
                
                -- Fixed scoring
                WHEN ss.scoring_metadata->>'type' = 'fixed' THEN
                    COALESCE((ss.scoring_metadata->>'score')::numeric, 0.5)
                    
                ELSE 0.5
            END AS normalized_score
        FROM gene_evidence ge
        JOIN genes g ON ge.gene_id = g.id
        JOIN static_sources ss ON ge.source_name = 'ingested_' || ss.id::text
        WHERE ss.is_active = true;
    """)

def downgrade():
    # Drop views
    op.execute("DROP VIEW IF EXISTS static_evidence_scores")
    op.execute("DROP VIEW IF EXISTS static_evidence_counts")
    
    # Drop indexes
    op.drop_index('idx_audit_source_id')
    op.drop_index('idx_uploads_hash')
    op.drop_index('idx_uploads_status')
    op.drop_index('idx_uploads_source_id')
    op.drop_index('idx_static_sources_active')
    op.drop_index('idx_static_sources_type')
    
    # Drop tables
    op.drop_table('static_source_audit')
    op.drop_table('static_evidence_uploads')
    op.drop_table('static_sources')
```

### 2. Core Processing Engine with Enhanced JSON Parsing

```python
# backend/app/core/static_ingestion.py

import asyncio
import hashlib
import json
import os
import tempfile
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.gene_normalizer import normalize_genes_batch_async
from app.models.gene import GeneEvidence
from app.models.gene_staging import GeneNormalizationStaging
from app.models.static_ingestion import (
    StaticEvidenceUpload,
    StaticSource,
    StaticSourceAudit,
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
    ) -> Dict[str, Any]:
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
                        "message": f"This file was already processed on {existing.uploaded_at}"
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
                    upload.metadata['provider'] = result['provider_metadata']
                
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
    
    def _parse_file_content(self, content: bytes, file_type: str) -> tuple[List[Dict], Dict]:
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
        symbols: List[str], 
        source_id: int
    ) -> Dict[str, Dict]:
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
            
            normalization_map.update(batch_results)
            
            # Rate limit between batches
            if i + self.normalization_batch_size < len(symbols):
                await asyncio.sleep(self.rate_limit_delay)
        
        return normalization_map
    
    async def _process_small_file_batch(
        self,
        content: bytes,
        file_type: str,
        file_hash: str,
        source_id: int,
        evidence_name: str,
        filename: str,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Process small files with batch normalization."""
        
        # Parse content and extract metadata
        genes_data, file_metadata = self._parse_file_content(content, file_type)
        
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
        
        if not symbol_to_entries:
            return {
                "status": "error",
                "message": "No valid gene symbols found"
            }
        
        # Batch normalize all unique symbols
        unique_symbols = list(symbol_to_entries.keys())
        logger.info(f"Found {len(unique_symbols):,} unique symbols from {len(genes_data):,} entries")
        
        normalization_map = await self._batch_normalize_all_symbols(
            unique_symbols, source_id
        )
        
        # Process results
        total_stats = {
            "total_genes": len(genes_data),
            "normalized": 0,
            "staged": 0,
            "failed": 0
        }
        
        evidence_batch = []
        staging_batch = []
        
        # Use safe source name to prevent collisions
        source_name = f"ingested_{source_id}"
        
        for symbol, entries in symbol_to_entries.items():
            result = normalization_map.get(symbol, {"status": "failed"})
            
            for unique_key, entry in entries:
                if result['status'] == 'success' and result.get('gene_id'):
                    total_stats["normalized"] += 1
                    
                    if not dry_run:
                        # Build evidence data preserving all fields
                        evidence_data = {
                            "original_symbol": symbol,
                            "confidence": entry.get("confidence", "medium"),
                        }
                        
                        # Preserve panels from scraper data
                        if "panels" in entry:
                            evidence_data["panels"] = entry["panels"]
                        
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
                            "gene_id": result['gene_id'],
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
                    self._bulk_insert_evidence(evidence_batch)
                if staging_batch:
                    self._bulk_insert_staging(staging_batch)
                self.db.commit()
            except Exception as e:
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
    ) -> Dict[str, Any]:
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
        source_name = f"ingested_{source_id}"
        
        # Process normalization results
        for symbol, entries in symbol_to_entries.items():
            result = normalization_map.get(symbol, {"status": "failed"})
            
            for unique_key, entry in entries:
                if result['status'] == 'success' and result.get('gene_id'):
                    total_stats["normalized"] += 1
                    
                    if not dry_run:
                        evidence_data = {
                            "original_symbol": symbol,
                            "confidence": entry.get("confidence", "medium"),
                            "metadata": {k: v for k, v in entry.items() 
                                       if k not in ['symbol', 'gene_symbol', 'gene', 'confidence']}
                        }
                        
                        evidence_batch.append({
                            "gene_id": result['gene_id'],
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
                        self._bulk_insert_evidence(evidence_batch)
                        self.db.commit()
                        evidence_batch = []
                        logger.info(f"Inserted batch, progress: {total_stats['normalized']:,} normalized")
                    except Exception as e:
                        self.db.rollback()
                        raise
                
                if len(staging_batch) >= 500:
                    try:
                        self._bulk_insert_staging(staging_batch)
                        self.db.commit()
                        staging_batch = []
                    except Exception as e:
                        self.db.rollback()
                        raise
        
        # Final inserts
        if not dry_run:
            try:
                if evidence_batch:
                    self._bulk_insert_evidence(evidence_batch)
                if staging_batch:
                    self._bulk_insert_staging(staging_batch)
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                raise
        
        logger.info(f"Upload complete: {total_stats}")
        
        return {
            "status": "success",
            "stats": total_stats
        }
    
    def _extract_gene_symbol(self, entry: Dict) -> Optional[str]:
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
    
    def _calculate_priority(self, entry: Dict) -> int:
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
    
    def _bulk_insert_evidence(self, evidence_batch: List[Dict]):
        """Efficiently insert evidence in bulk"""
        if not evidence_batch:
            return
        
        # Use SQLAlchemy bulk insert
        self.db.bulk_insert_mappings(GeneEvidence, evidence_batch)
        self.db.flush()
        logger.info(f"Bulk inserted {len(evidence_batch)} evidence records")
    
    def _bulk_insert_staging(self, staging_batch: List[Dict]):
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
```

### 3. API Implementation

```python
# backend/app/schemas/ingestion.py

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

class ScoringMetadata(BaseModel):
    """Scoring configuration for static sources"""
    type: str = Field(
        ..., 
        pattern="^(count|classification|fixed)$",
        description="Scoring type: count, classification, or fixed"
    )
    field: Optional[str] = Field(
        None,
        description="JSON field to use for scoring (for count/classification types)"
    )
    weight: Optional[float] = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Weight multiplier for count-based scoring"
    )
    weight_map: Optional[Dict[str, float]] = Field(
        None,
        description="Classification to score mapping (for classification type)"
    )
    score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Fixed score (for fixed type)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "count",
                    "field": "panels",
                    "weight": 0.7
                },
                {
                    "type": "classification",
                    "field": "confidence",
                    "weight_map": {
                        "high": 1.0,
                        "medium": 0.6,
                        "low": 0.3
                    }
                },
                {
                    "type": "fixed",
                    "score": 0.5
                }
            ]
        }
    )

class StaticSourceCreate(BaseModel):
    """Create a new static source"""
    source_type: str = Field(..., pattern="^(diagnostic_panel|manual_curation|literature_review|custom)$")
    source_name: str = Field(..., min_length=1, max_length=255)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    scoring_metadata: ScoringMetadata = Field(
        default_factory=lambda: ScoringMetadata(type="count", weight=0.5)
    )

class StaticSourceUpdate(BaseModel):
    """Update static source configuration"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    scoring_metadata: Optional[ScoringMetadata] = None
    is_active: Optional[bool] = None

class StaticSourceResponse(BaseModel):
    """Static source response"""
    id: int
    source_type: str
    source_name: str
    display_name: str
    description: Optional[str]
    metadata: Dict[str, Any]
    scoring_metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    
    # Statistics
    upload_count: Optional[int] = None
    total_genes: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class UploadResponse(BaseModel):
    """Upload response"""
    status: str
    upload_id: Optional[int] = None
    stats: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    provider_metadata: Optional[Dict[str, Any]] = None

class AuditLogResponse(BaseModel):
    """Audit log entry"""
    id: int
    source_id: int
    upload_id: Optional[int]
    action: str
    details: Dict[str, Any]
    performed_by: Optional[str]
    performed_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

```python
# backend/app/api/endpoints/ingestion.py

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.static_ingestion import StaticContentProcessor
from app.models.static_ingestion import (
    StaticEvidenceUpload,
    StaticSource,
    StaticSourceAudit,
)
from app.schemas.ingestion import (
    AuditLogResponse,
    StaticSourceCreate,
    StaticSourceResponse,
    StaticSourceUpdate,
    UploadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])

@router.post("/sources", response_model=StaticSourceResponse)
async def create_source(
    source: StaticSourceCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new static source with scoring configuration"""
    
    # Check for duplicate
    existing = db.query(StaticSource).filter(
        StaticSource.source_name == source.source_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source '{source.source_name}' already exists"
        )
    
    # Create source with scoring metadata
    db_source = StaticSource(
        source_type=source.source_type,
        source_name=source.source_name,
        display_name=source.display_name,
        description=source.description,
        metadata=source.metadata or {},
        scoring_metadata=source.scoring_metadata.model_dump(),
        created_by=current_user.email if current_user else None
    )
    db.add(db_source)
    db.flush()
    
    # Audit
    audit = StaticSourceAudit(
        source_id=db_source.id,
        action="created",
        details={
            "source": source.model_dump(),
            "scoring": source.scoring_metadata.model_dump()
        },
        performed_by=current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()
    
    # Add statistics
    db_source.upload_count = 0
    db_source.total_genes = 0
    
    return db_source

@router.get("/sources", response_model=List[StaticSourceResponse])
async def list_sources(
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all static sources"""
    query = db.query(StaticSource)
    
    if active_only:
        query = query.filter(StaticSource.is_active == True)
    
    sources = query.all()
    
    # Add statistics
    for source in sources:
        source.upload_count = db.query(func.count(StaticEvidenceUpload.id)).filter(
            StaticEvidenceUpload.source_id == source.id,
            StaticEvidenceUpload.upload_status == 'completed'
        ).scalar()
        
        source.total_genes = db.query(func.sum(StaticEvidenceUpload.genes_normalized)).filter(
            StaticEvidenceUpload.source_id == source.id,
            StaticEvidenceUpload.upload_status == 'completed'
        ).scalar() or 0
    
    return sources

@router.get("/sources/{source_id}", response_model=StaticSourceResponse)
async def get_source(
    source_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific static source"""
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Add statistics
    source.upload_count = db.query(func.count(StaticEvidenceUpload.id)).filter(
        StaticEvidenceUpload.source_id == source.id,
        StaticEvidenceUpload.upload_status == 'completed'
    ).scalar()
    
    source.total_genes = db.query(func.sum(StaticEvidenceUpload.genes_normalized)).filter(
        StaticEvidenceUpload.source_id == source.id,
        StaticEvidenceUpload.upload_status == 'completed'
    ).scalar() or 0
    
    return source

@router.put("/sources/{source_id}", response_model=StaticSourceResponse)
async def update_source(
    source_id: int,
    update: StaticSourceUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update source including scoring configuration"""
    
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    # Track changes for audit
    changes = {}
    
    if update.display_name is not None:
        changes["display_name"] = {"old": source.display_name, "new": update.display_name}
        source.display_name = update.display_name
    
    if update.description is not None:
        changes["description"] = {"old": source.description, "new": update.description}
        source.description = update.description
    
    if update.metadata is not None:
        changes["metadata"] = {"old": source.metadata, "new": update.metadata}
        source.metadata = update.metadata
    
    if update.scoring_metadata is not None:
        changes["scoring_metadata"] = {
            "old": source.scoring_metadata, 
            "new": update.scoring_metadata.model_dump()
        }
        source.scoring_metadata = update.scoring_metadata.model_dump()
        
        # Note: Score recalculation happens via view definitions
    
    if update.is_active is not None:
        changes["is_active"] = {"old": source.is_active, "new": update.is_active}
        source.is_active = update.is_active
    
    source.updated_at = datetime.utcnow()
    
    # Audit
    audit = StaticSourceAudit(
        source_id=source_id,
        action="updated",
        details={"changes": changes},
        performed_by=current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()
    
    return source

@router.post("/sources/{source_id}/upload", response_model=UploadResponse)
async def upload_evidence(
    source_id: int,
    file: UploadFile = File(...),
    evidence_name: Optional[str] = Form(None),
    replace_existing: bool = Form(False),
    dry_run: bool = Form(False),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Upload evidence file (JSON, CSV, TSV, Excel).
    Handles scraper outputs and manual uploads.
    """
    
    # Validate source
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id,
        StaticSource.is_active == True
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found or inactive"
        )
    
    # Size validation
    file_size = 0
    temp_content = await file.read()
    file_size = len(temp_content)
    await file.seek(0)  # Reset for processing
    
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit"
        )
    
    # Default evidence name
    if not evidence_name:
        evidence_name = file.filename.rsplit('.', 1)[0]
    
    # Check existing
    if not replace_existing:
        existing = db.query(StaticEvidenceUpload).filter(
            StaticEvidenceUpload.source_id == source_id,
            StaticEvidenceUpload.evidence_name == evidence_name,
            StaticEvidenceUpload.upload_status != 'superseded'
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Evidence '{evidence_name}' already exists. Set replace_existing=true to update."
            )
    elif not dry_run:
        # Mark existing as superseded
        db.query(StaticEvidenceUpload).filter(
            StaticEvidenceUpload.source_id == source_id,
            StaticEvidenceUpload.evidence_name == evidence_name,
            StaticEvidenceUpload.upload_status != 'superseded'
        ).update({"upload_status": "superseded"})
        db.commit()
    
    # Process with batch normalization
    processor = StaticContentProcessor(db)
    result = await processor.process_upload(
        file=file,
        source_id=source_id,
        evidence_name=evidence_name,
        dry_run=dry_run
    )
    
    # Audit
    if not dry_run and result["status"] == "success":
        audit = StaticSourceAudit(
            source_id=source_id,
            upload_id=result.get("upload_id"),
            action="uploaded",
            details={
                "evidence_name": evidence_name,
                "filename": file.filename,
                "stats": result.get("stats"),
                "provider_metadata": result.get("provider_metadata")
            },
            performed_by=current_user.email if current_user else None
        )
        db.add(audit)
        db.commit()
    
    return result

@router.get("/sources/{source_id}/uploads", response_model=List[Dict])
async def list_uploads(
    source_id: int,
    db: Session = Depends(get_db)
):
    """List all uploads for a source"""
    uploads = db.query(StaticEvidenceUpload).filter(
        StaticEvidenceUpload.source_id == source_id
    ).order_by(StaticEvidenceUpload.uploaded_at.desc()).all()
    
    return [
        {
            "id": u.id,
            "evidence_name": u.evidence_name,
            "original_filename": u.original_filename,
            "upload_status": u.upload_status,
            "gene_count": u.gene_count,
            "genes_normalized": u.genes_normalized,
            "genes_failed": u.genes_failed,
            "genes_staged": u.genes_staged,
            "uploaded_at": u.uploaded_at,
            "processed_at": u.processed_at,
            "uploaded_by": u.uploaded_by,
            "metadata": u.metadata
        }
        for u in uploads
    ]

@router.get("/sources/{source_id}/audit", response_model=List[AuditLogResponse])
async def get_audit_log(
    source_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get audit log for a source"""
    logs = db.query(StaticSourceAudit).filter(
        StaticSourceAudit.source_id == source_id
    ).order_by(StaticSourceAudit.performed_at.desc()).limit(limit).all()
    
    return logs

@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Soft delete a source (mark as inactive)"""
    
    source = db.query(StaticSource).filter(
        StaticSource.id == source_id
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found"
        )
    
    source.is_active = False
    source.updated_at = datetime.utcnow()
    
    # Audit
    audit = StaticSourceAudit(
        source_id=source_id,
        action="deactivated",
        details={},
        performed_by=current_user.email if current_user else None
    )
    db.add(audit)
    db.commit()
    
    return {"status": "success", "message": f"Source {source_id} deactivated"}
```

### 4. Add to Main Application

```python
# backend/app/main.py
# Add to existing imports and routers

from app.api.endpoints import ingestion

# Add to router registration
app.include_router(ingestion.router)
```

```python
# backend/app/models/__init__.py
# Add to existing imports

from app.models.static_ingestion import (
    StaticSource,
    StaticEvidenceUpload,
    StaticSourceAudit
)
```

## Usage Examples

### 1. Upload Scraper Output

```bash
# Create source for Blueprint Genetics
curl -X POST http://localhost:8000/api/v1/ingestion/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "diagnostic_panel",
    "source_name": "blueprint_genetics",
    "display_name": "Blueprint Genetics Panels",
    "description": "Kidney disease panels from Blueprint Genetics",
    "scoring_metadata": {
      "type": "count",
      "field": "panels",
      "weight": 0.8
    }
  }'

# Upload scraper JSON output
curl -X POST http://localhost:8000/api/v1/ingestion/sources/1/upload \
  -F "file=@scrapers/output/blueprint_genetics_20250120.json" \
  -F "evidence_name=Blueprint January 2025"

# Response includes provider metadata extracted from JSON
{
  "status": "success",
  "upload_id": 123,
  "stats": {
    "total_genes": 450,
    "normalized": 420,
    "staged": 25,
    "failed": 5
  },
  "provider_metadata": {
    "id": "blueprint_genetics",
    "name": "Blueprint Genetics",
    "type": "diagnostic_panel",
    "scraped_at": "2025-01-20T10:30:00"
  }
}
```

### 2. Upload Manual CSV

```bash
# Create source for manual curation
curl -X POST http://localhost:8000/api/v1/ingestion/sources \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "manual_curation",
    "source_name": "expert_review_2025",
    "display_name": "Expert Review 2025",
    "scoring_metadata": {
      "type": "classification",
      "field": "confidence",
      "weight_map": {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3
      }
    }
  }'

# Upload CSV
curl -X POST http://localhost:8000/api/v1/ingestion/sources/2/upload \
  -F "file=@manual_genes.csv" \
  -F "evidence_name=Q1 2025 Review"
```

### 3. Query Evidence Scores

```sql
-- Get scores for static sources
SELECT 
    g.approved_symbol,
    ses.source_display_name,
    ses.normalized_score
FROM static_evidence_scores ses
JOIN genes g ON ses.gene_id = g.id
WHERE g.approved_symbol = 'PKD1'
ORDER BY ses.normalized_score DESC;

-- Combine with existing evidence scores
SELECT 
    gene_id,
    approved_symbol,
    source_name,
    normalized_score
FROM evidence_normalized_scores
WHERE source_name IN ('PanelApp', 'GenCC', 'ClinGen')

UNION ALL

SELECT 
    gene_id,
    approved_symbol,
    source_name,
    normalized_score
FROM static_evidence_scores;
```

## Testing

```python
# backend/tests/test_static_ingestion_scraper.py

import json
import pytest
from sqlalchemy.orm import Session

@pytest.mark.asyncio
async def test_scraper_json_upload(db: Session, test_client):
    """Test uploading scraper JSON output"""
    
    # Create source
    source_data = {
        "source_type": "diagnostic_panel",
        "source_name": "test_scraper",
        "display_name": "Test Scraper",
        "scoring_metadata": {
            "type": "count",
            "field": "panels",
            "weight": 0.7
        }
    }
    
    response = await test_client.post("/api/v1/ingestion/sources", json=source_data)
    assert response.status_code == 200
    source_id = response.json()["id"]
    
    # Prepare scraper format JSON
    scraper_data = {
        "provider_id": "test_provider",
        "provider_name": "Test Provider",
        "provider_type": "diagnostic_panel",
        "main_url": "https://example.com",
        "scraped_at": "2025-01-20T10:00:00",
        "genes": [
            {
                "symbol": "PKD1",
                "panels": ["Polycystic Kidney Disease", "Ciliopathy"],
                "occurrence_count": 2,
                "confidence": "high",
                "hgnc_id": "HGNC:9008"
            },
            {
                "symbol": "PKD2",
                "panels": ["Polycystic Kidney Disease"],
                "occurrence_count": 1,
                "confidence": "high",
                "hgnc_id": "HGNC:9009"
            }
        ]
    }
    
    # Upload file
    files = {
        "file": ("scraper_output.json", json.dumps(scraper_data), "application/json")
    }
    response = await test_client.post(
        f"/api/v1/ingestion/sources/{source_id}/upload",
        files=files,
        data={"evidence_name": "Test Scraper Data"}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "success"
    assert result["provider_metadata"]["id"] == "test_provider"
    assert result["stats"]["total_genes"] == 2
    
    # Verify evidence was created with panels preserved
    from app.models.gene import GeneEvidence
    evidence = db.query(GeneEvidence).filter(
        GeneEvidence.source_name == f"ingested_{source_id}"
    ).first()
    
    assert evidence is not None
    assert "panels" in evidence.evidence_data
    assert len(evidence.evidence_data["panels"]) > 0
```

## Performance Metrics

| Metric | Target | Implementation |
|--------|--------|---------------|
| 1000 gene normalization | <5 seconds | Batch API calls with rate limiting |
| 10MB file processing | <30 seconds | Chunked processing |
| 50MB file memory usage | <500MB | Streaming with temp files |
| Duplicate detection | <100ms | Hash-based with index |
| API rate limiting | 10 req/sec | 100ms delay between batches |

## Deployment Checklist

### Pre-Deployment
- [ ] Run Alembic migration to create tables
- [ ] Test with actual scraper JSON outputs
- [ ] Verify rate limiting prevents API overload
- [ ] Test 50MB file upload
- [ ] Verify separate scoring views work

### Deployment
- [ ] Deploy database migration
- [ ] Deploy backend with new models
- [ ] Register ingestion router
- [ ] Test metadata extraction from scraper files
- [ ] Verify scoring calculations

### Post-Deployment
- [ ] Monitor HGNC API usage
- [ ] Check memory usage for large files
- [ ] Verify evidence scores
- [ ] Review audit logs

## Conclusion

This production implementation provides:

1. **Universal File Handler**: Handles scraper JSON, CSV, TSV, Excel without special cases
2. **Provider Metadata Extraction**: Preserves scraper metadata (provider info, panels)
3. **Safe Source Names**: Uses `ingested_{id}` pattern to prevent collisions
4. **Rate-Limited Batch Processing**: Prevents HGNC API overload
5. **Non-Breaking Integration**: Separate views preserve existing scoring
6. **Complete Audit Trail**: Full tracking of all operations
7. **Transaction Safety**: Proper rollback on failures

The system is production-ready and fully handles the existing scraper output format while remaining flexible for other file types.