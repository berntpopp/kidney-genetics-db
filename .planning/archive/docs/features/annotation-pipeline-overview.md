# Annotation Pipeline Overview

## Current Status
The annotation pipeline is fully operational with smart update strategies, background processing, and comprehensive admin controls.

## Implemented Features

### Core Functionality
- **9 Annotation Sources**: HGNC, ClinVar, Descartes, gnomAD, GTEx, HPO, MPO/MGI, STRING PPI, PubTator
- **Smart Update Strategies**:
  - FULL: Complete re-annotation of all genes
  - INCREMENTAL: Update only genes modified since last run
  - SELECTIVE: Target specific sources or genes
- **Background Processing**: All updates run asynchronously without blocking API
- **Progress Tracking**: Real-time WebSocket updates with pause/resume capability
- **Admin Controls**: Full pipeline management through admin interface

### Performance Metrics
- **API Response Times**: 7-13ms during pipeline execution (down from 5-10 seconds)
- **Cache Hit Rate**: 75-95%
- **Annotation Coverage**: 95%+ genes have annotations
- **Update Frequency**: Quarterly (90-day) schedule for all sources

## Architecture

### Key Components
```
backend/app/pipeline/
├── annotation_pipeline.py      # Main orchestrator
├── sources/annotations/        # Individual source implementations
│   ├── base.py                # Base class with caching/retry
│   ├── clinvar.py            # ClinVar variants
│   ├── hgnc.py               # Gene nomenclature
│   └── [other sources]
└── progress_tracker.py        # Real-time progress updates
```

### Update Flow
1. Admin triggers update via UI or scheduler
2. Pipeline runs in background with progress tracking
3. Sources fetch data with automatic retry/rate limiting
4. Annotations cached in PostgreSQL JSONB
5. WebSocket broadcasts real-time progress

## Admin Interface

### Available Actions
- **Run Updates**: Trigger FULL/INCREMENTAL/SELECTIVE updates
- **Manage Sources**: Enable/disable, set update frequencies
- **Monitor Progress**: Real-time progress with pause/resume
- **Clear Cache**: Invalidate cached annotations
- **Reset Annotations**: Clear annotations (admin-only)

### API Endpoints
- `GET /api/annotations/sources` - List all sources with status
- `POST /api/annotations/pipeline/run` - Trigger pipeline update
- `GET /api/annotations/pipeline/status` - Get current status
- `POST /api/annotations/pipeline/pause` - Pause running update
- `POST /api/annotations/pipeline/resume` - Resume paused update
- `DELETE /api/annotations/reset` - Clear annotations (Issue #9)

## Known Issues & Solutions

### Database Connection Drops
- **Issue**: PostgreSQL connections timeout during long operations
- **Solution**: Implemented connection pooling with automatic reconnection

### Rate Limiting
- **Issue**: External APIs (especially ClinVar) have strict rate limits
- **Solution**: Exponential backoff retry with configurable delays per source

### Memory Usage
- **Issue**: Large batch operations could consume excessive memory
- **Solution**: Streaming processing with configurable batch sizes

## Configuration

### Source Settings (90-day quarterly updates)
```python
# backend/app/pipeline/sources/annotations/[source].py
cache_ttl_days = 90
update_frequency = "quarterly"
```

### Performance Tuning
```python
# Batch sizes for optimal performance
BATCH_SIZE = 100  # Genes per batch
MAX_WORKERS = 3   # Parallel source fetches
CACHE_TTL = 7776000  # 90 days in seconds
```

## Maintenance

### Monitoring
- Check `/api/annotations/pipeline/status` for pipeline health
- Review system logs for rate limit errors
- Monitor cache hit rates via admin panel

### Troubleshooting
1. **Pipeline Stuck**: Use pause/resume to restart
2. **Rate Limits**: Reduce batch size or increase delays
3. **Missing Annotations**: Run SELECTIVE update for specific source
4. **Cache Issues**: Clear cache and run INCREMENTAL update

## Future Enhancements
- Differential updates (only changed fields)
- Source-specific scheduling
- Automated quality checks
- Annotation versioning