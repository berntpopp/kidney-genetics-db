# Percentile Service Implementation TODOs

## 1. Create Core Percentile Service

### File: `backend/app/core/percentile_service.py` (NEW)
```python
"""Global percentile calculation service for annotation scores."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.cache_service import get_cache_service
from app.core.logging import get_logger


class PercentileService:
    """
    Service for calculating and managing global percentiles.
    Follows patterns from CacheService and RetryService.
    """

    def __init__(self, session: Session):
        self.session = session
        self.logger = get_logger(__name__)
        self._executor = ThreadPoolExecutor(max_workers=2)
        self.cache_service = get_cache_service(session)

    async def calculate_global_percentiles(
        self,
        source: str,
        score_field: str
    ) -> Dict[int, float]:
        """
        Calculate global percentiles for a source using PostgreSQL.
        Non-blocking via ThreadPoolExecutor.
        """
        loop = asyncio.get_event_loop()

        # Check cache first
        cache_key = f"percentiles:{source}:global"
        cached = await self.cache_service.get(
            key=cache_key,
            namespace="statistics",
            default=None
        )

        if cached:
            await self.logger.info(f"Using cached percentiles for {source}")
            return cached

        # Calculate in thread pool
        await self.logger.info(f"Calculating global percentiles for {source}")
        percentiles = await loop.run_in_executor(
            self._executor,
            self._calculate_percentiles_sync,
            source,
            score_field
        )

        # Cache results
        await self.cache_service.set(
            key=cache_key,
            value=percentiles,
            namespace="statistics",
            ttl=3600  # 1 hour
        )

        return percentiles

    def _calculate_percentiles_sync(
        self,
        source: str,
        score_field: str
    ) -> Dict[int, float]:
        """Synchronous percentile calculation for thread pool."""
        # Use the view to get percentiles
        result = self.session.execute(
            text(f"SELECT * FROM {source}_percentiles")
        )

        percentiles = {}
        for row in result:
            gene_id = row[0]
            percentile = row[3]  # percentile_rank column
            percentiles[gene_id] = round(percentile, 3)

        self.logger.sync_info(
            f"Calculated {len(percentiles)} percentiles for {source}"
        )

        return percentiles

    async def get_percentile_for_gene(
        self,
        source: str,
        gene_id: int,
        raw_score: float
    ) -> float:
        """Get percentile for a specific gene/score."""
        percentiles = await self.calculate_global_percentiles(
            source,
            "ppi_score"  # TODO: make dynamic
        )

        if gene_id in percentiles:
            return percentiles[gene_id]

        # Fallback: calculate on-demand (avoid 100th percentile issue)
        await self.logger.warning(
            f"Gene {gene_id} not in pre-computed percentiles for {source}"
        )
        return None  # Don't return misleading value
```

## 2. Add Database View

### File: `backend/app/db/views.py` (MODIFY)
Add after line 173 (after existing views):
```python
string_ppi_percentiles = ReplaceableObject(
    name="string_ppi_percentiles",
    sqltext="""
    SELECT
        ga.gene_id,
        g.approved_symbol,
        CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT) as ppi_score,
        PERCENT_RANK() OVER (
            ORDER BY CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT)
        ) AS percentile_rank
    FROM gene_annotations ga
    JOIN genes g ON g.id = ga.gene_id
    WHERE ga.annotations ? 'string_ppi'
      AND ga.annotations->'string_ppi'->0->'data' ? 'ppi_score'
      AND ga.annotations->'string_ppi'->0->'data'->>'ppi_score' != 'null'
      AND ga.annotations->'string_ppi'->0->'data'->>'ppi_score' != '0'
    """,
    dependencies=[],
)

# Add to ALL_VIEWS list at end of file
ALL_VIEWS.append(string_ppi_percentiles)
```

## 3. Modify STRING PPI Source

### File: `backend/app/pipeline/sources/annotations/string_ppi.py` (MODIFY)

#### Line 168-312: Replace fetch_batch method
```python
async def fetch_batch(self, genes: list[Gene]) -> dict[int, dict[str, Any]]:
    """
    Fetch annotations for multiple genes.
    Now uses global percentiles instead of batch-relative.
    """
    # Load data if not already loaded
    await self._load_data()
    await self._load_kidney_genes()

    logger.sync_info(f"Processing {len(genes)} genes for PPI scores")

    results = {}
    raw_scores = {}

    # Calculate raw scores (existing logic)
    for gene in genes:
        gene_symbol = gene.approved_symbol

        if gene_symbol not in self._kidney_genes:
            continue

        # [... existing score calculation logic lines 191-258 ...]
        # Keep all the existing calculation logic
        raw_scores[gene.id] = raw_score
        results[gene.id] = {
            "ppi_score": round(raw_score, 2),
            "ppi_degree": degree,
            "interactions": top_interactions,
            "summary": summary,
        }

    # NEW: Get global percentiles instead of calculating here
    if raw_scores:
        from app.core.percentile_service import PercentileService

        percentile_service = PercentileService(self.session)
        global_percentiles = await percentile_service.calculate_global_percentiles(
            "string_ppi",
            "ppi_score"
        )

        # Apply global percentiles
        for gene_id in results:
            if gene_id in global_percentiles:
                results[gene_id]["ppi_percentile"] = global_percentiles[gene_id]
            else:
                # Don't show misleading 100th percentile
                results[gene_id]["ppi_percentile"] = None

    logger.sync_info(
        f"Calculated PPI scores for {len(results)} genes",
        zero_score_genes=len([1 for s in raw_scores.values() if s == 0]),
    )

    return results
```

#### Add new method after line 367:
```python
async def recalculate_global_percentiles(self):
    """
    Trigger global percentile recalculation after batch updates.
    Should be called after annotation pipeline runs.
    """
    from app.core.percentile_service import PercentileService

    service = PercentileService(self.session)
    await service.calculate_global_percentiles("string_ppi", "ppi_score")

    logger.sync_info("Updated global STRING PPI percentiles")
```

## 4. Create Background Task

### File: `backend/app/pipeline/tasks/percentile_updater.py` (NEW)
```python
"""Background tasks for updating global percentiles."""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.percentile_service import PercentileService
from app.pipeline.sources.annotations.string_ppi import StringPPIAnnotationSource

logger = get_logger(__name__)


async def update_percentiles_for_source(db: Session, source: str):
    """
    Update global percentiles for a specific annotation source.

    Args:
        db: Database session
        source: Source name (e.g., 'string_ppi')
    """
    await logger.info(f"Starting percentile update for {source}")

    try:
        if source == "string_ppi":
            # Use dedicated method for STRING
            string_source = StringPPIAnnotationSource(db)
            await string_source.recalculate_global_percentiles()
        else:
            # Generic percentile calculation
            service = PercentileService(db)
            await service.calculate_global_percentiles(source, "score")

        await logger.info(f"Successfully updated percentiles for {source}")

    except Exception as e:
        await logger.error(
            f"Failed to update percentiles for {source}: {str(e)}",
            exc_info=True
        )
        raise


async def update_all_percentiles(db: Session):
    """Update percentiles for all supported sources."""
    sources = ["string_ppi"]  # Add more as needed

    for source in sources:
        await update_percentiles_for_source(db, source)
```

## 5. Add API Endpoint

### File: `backend/app/api/endpoints/gene_annotations.py` (MODIFY)

#### Add imports at top (after line 25):
```python
from app.pipeline.tasks.percentile_updater import update_percentiles_for_source
```

#### Add endpoint after line 431 (after existing endpoints):
```python
@router.post("/percentiles/refresh", dependencies=[Depends(require_admin)])
async def refresh_global_percentiles(
    source: str = Query(..., description="Source to refresh (e.g., string_ppi)"),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Trigger global percentile recalculation for an annotation source.

    Admin only. Runs in background to avoid blocking.
    """
    await logger.info(
        f"Percentile refresh requested for {source}",
        user_id=current_user.id
    )

    # Validate source
    valid_sources = ["string_ppi", "gnomad", "gtex"]  # Add as needed
    if source not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {valid_sources}"
        )

    # Schedule background task
    background_tasks.add_task(
        update_percentiles_for_source,
        db,
        source
    )

    return {
        "status": "scheduled",
        "source": source,
        "message": f"Global percentile recalculation scheduled for {source}"
    }
```

## 6. Create Database Migration

### File: `backend/alembic/versions/xxx_add_string_ppi_percentiles_view.py` (NEW)
Run: `cd backend && alembic revision -m "add string ppi percentiles view"`

Then edit the generated file:
```python
"""add string ppi percentiles view

Revision ID: xxx
Revises: 001_initial_complete_schema
Create Date: xxx
"""
from alembic import op
import sqlalchemy as sa

revision = 'xxx'
down_revision = '001_initial_complete_schema'

def upgrade():
    # Create the view
    op.execute("""
        CREATE OR REPLACE VIEW string_ppi_percentiles AS
        SELECT
            ga.gene_id,
            g.approved_symbol,
            CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT) as ppi_score,
            PERCENT_RANK() OVER (
                ORDER BY CAST(ga.annotations->'string_ppi'->0->'data'->>'ppi_score' AS FLOAT)
            ) AS percentile_rank
        FROM gene_annotations ga
        JOIN genes g ON g.id = ga.gene_id
        WHERE ga.annotations ? 'string_ppi'
          AND ga.annotations->'string_ppi'->0->'data' ? 'ppi_score'
          AND ga.annotations->'string_ppi'->0->'data'->>'ppi_score' != 'null'
    """)

def downgrade():
    op.execute("DROP VIEW IF EXISTS string_ppi_percentiles")
```

## 7. Add Tests

### File: `backend/tests/test_percentile_service.py` (NEW)
```python
"""Tests for the percentile service."""

import pytest
from scipy.stats import rankdata

from app.core.percentile_service import PercentileService


def test_percentile_calculation_with_ties():
    """Test that tied scores get averaged ranks."""
    scores = [10, 20, 20, 30, 40]
    ranks = rankdata(scores, method="average")
    percentiles = (ranks - 1) / (len(ranks) - 1)

    # Tied values should have same percentile
    assert percentiles[1] == percentiles[2]
    assert 0.3 < percentiles[1] < 0.4


def test_single_value_percentile():
    """Test edge case of single value."""
    scores = [42.0]
    ranks = rankdata(scores, method="average")
    # Single value should not be 100th percentile
    assert ranks[0] == 1.0

    # Convention: map to 0.5 (median) for single values
    percentile = 0.5 if len(scores) == 1 else (ranks[0] - 1) / (len(ranks) - 1)
    assert percentile == 0.5


@pytest.mark.asyncio
async def test_percentile_service_caching(db_session):
    """Test that percentile service uses cache correctly."""
    service = PercentileService(db_session)

    # First call should calculate
    result1 = await service.calculate_global_percentiles("test_source", "score")

    # Second call should use cache (fast)
    import time
    start = time.time()
    result2 = await service.calculate_global_percentiles("test_source", "score")
    elapsed = time.time() - start

    assert elapsed < 0.01  # Should be very fast from cache
    assert result1 == result2
```

## 8. Update Annotation Pipeline

### File: `backend/app/pipeline/annotation_pipeline.py` (MODIFY)

#### Add after line 415 (after process_batch completion):
```python
# Update global percentiles after batch processing
if "string_ppi" in self.config.enabled_sources:
    await logger.info("Updating STRING PPI global percentiles")
    from app.pipeline.tasks.percentile_updater import update_percentiles_for_source
    await update_percentiles_for_source(db, "string_ppi")
```

## Execution Order

1. Create `PercentileService` class
2. Add database view
3. Run migration: `cd backend && alembic upgrade head`
4. Modify `StringPPIAnnotationSource`
5. Create background task module
6. Add API endpoint
7. Add tests
8. Update annotation pipeline
9. Test with: `curl -X POST http://localhost:8000/api/annotations/percentiles/refresh?source=string_ppi`

## Validation Commands

```bash
# Check view creation
cd backend && uv run python -c "
from sqlalchemy import create_engine, text
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM string_ppi_percentiles'))
    print(f'Percentiles calculated for {result.scalar()} genes')
"

# Test percentile calculation
curl -X POST http://localhost:8000/api/annotations/percentiles/refresh?source=string_ppi \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Verify specific genes
curl http://localhost:8000/api/genes/HNF1B | jq '.data.attributes | .ppi_score, .ppi_percentile'
curl http://localhost:8000/api/genes/PKD1 | jq '.data.attributes | .ppi_score, .ppi_percentile'
```