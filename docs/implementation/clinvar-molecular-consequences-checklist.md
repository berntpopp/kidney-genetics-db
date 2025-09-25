# ClinVar Molecular Consequences - Implementation Checklist

## Backend Changes (4 files)

### 1. `/backend/app/pipeline/sources/annotations/clinvar.py`

#### Change 1.1: Update `_parse_variant()` method (Line 147)
**Location**: Line 147 in result dictionary
**Add**: New field for molecular consequences
```python
# AFTER line 146 ("traits": []),
"molecular_consequences": variant_data.get("molecular_consequence_list", []),
```

#### Change 1.2: Update `_aggregate_variants()` method (Line 264-266)
**Location**: After line 266 in stats dictionary
**Add**: New tracking fields
```python
# AFTER line 266 ("traits_summary": defaultdict(int),),
"molecular_consequences": defaultdict(int),
"consequence_categories": {
    "truncating": 0,        # nonsense + frameshift + essential splice
    "missense": 0,          # missense variants
    "inframe": 0,           # inframe insertions/deletions
    "splice_region": 0,     # non-essential splice variants
    "regulatory": 0,        # UTR variants
    "intronic": 0,          # intronic variants
    "synonymous": 0,        # synonymous variants
    "other": 0,             # everything else
},
```

#### Change 1.3: Add categorization logic (After line 307)
**Location**: After line 307 (before "# Convert defaultdicts to regular dicts")
**Add**: New categorization logic
```python
# Define truncating consequences
TRUNCATING_CONSEQUENCES = {
    "nonsense", "frameshift variant",
    "splice donor variant", "splice acceptor variant"
}

# Process molecular consequences
for variant in variants:
    for consequence in variant.get("molecular_consequences", []):
        stats["molecular_consequences"][consequence] += 1

        # Categorize (count most severe category per variant)
        if consequence in TRUNCATING_CONSEQUENCES:
            stats["consequence_categories"]["truncating"] += 1
        elif "missense" in consequence.lower():
            stats["consequence_categories"]["missense"] += 1
        elif "synonymous" in consequence.lower():
            stats["consequence_categories"]["synonymous"] += 1
        elif "inframe" in consequence.lower():
            stats["consequence_categories"]["inframe"] += 1
        elif "splice" in consequence.lower() and consequence not in TRUNCATING_CONSEQUENCES:
            stats["consequence_categories"]["splice_region"] += 1
        elif "UTR" in consequence:
            stats["consequence_categories"]["regulatory"] += 1
        elif "intron" in consequence.lower():
            stats["consequence_categories"]["intronic"] += 1
        else:
            stats["consequence_categories"]["other"] += 1

# Get top 10 molecular consequences
top_consequences = sorted(
    stats["molecular_consequences"].items(),
    key=lambda x: x[1],
    reverse=True
)[:10]
stats["top_molecular_consequences"] = [
    {"consequence": c[0], "count": c[1]} for c in top_consequences
]

# Calculate percentages
if stats["total_count"] > 0:
    for category in stats["consequence_categories"]:
        stats[f"{category}_percentage"] = round(
            (stats["consequence_categories"][category] / stats["total_count"]) * 100, 1
        )
```

#### Change 1.4: Update annotation dictionary (Line 435-437)
**Location**: After line 435 ("variant_types": stats["variant_type_counts"],)
**Add**: New annotation fields
```python
# AFTER line 435
"molecular_consequences": dict(stats["molecular_consequences"]),
"consequence_categories": stats["consequence_categories"],
"top_molecular_consequences": stats["top_molecular_consequences"],
"truncating_percentage": stats.get("truncating_percentage", 0),
"missense_percentage": stats.get("missense_percentage", 0),
"synonymous_percentage": stats.get("synonymous_percentage", 0),
```

### 2. `/backend/app/core/datasource_config.py` (OPTIONAL - for configuration)
**Location**: Add new section for ClinVar
**Add**: Configurable consequence groups
```python
# Add to DATA_SOURCE_CONFIG dictionary
"ClinVar": {
    # Existing config...
    "consequence_groups": {
        "truncating": [
            "nonsense",
            "frameshift variant",
            "stop gained",
            "splice donor variant",
            "splice acceptor variant",
        ],
        "missense": [
            "missense variant",
            "protein altering variant",
        ],
        "synonymous": [
            "synonymous variant",
            "silent variant",
        ],
        # Additional groups...
    }
}
```

## Frontend Changes (1 file)

### 3. `/frontend/src/components/gene/ClinVarVariants.vue`

#### Change 3.1: Add molecular consequences chip (After line 102)
**Location**: After the benign/likely benign chip closing tag (line 102)
**Add**: New chip for consequences
```vue
<!-- Molecular consequences chip (if data available) -->
<v-tooltip
  v-if="clinvarData.consequence_categories && clinvarData.total_variants > 0"
  location="bottom"
  max-width="400"
>
  <template #activator="{ props }">
    <v-chip
      color="deep-purple"
      variant="tonal"
      size="small"
      v-bind="props"
    >
      <v-icon size="x-small" start>mdi-dna</v-icon>
      Consequences
    </v-chip>
  </template>
  <div class="pa-2">
    <div class="font-weight-medium mb-2">Molecular Consequences</div>

    <!-- Highlight truncating if present -->
    <div
      v-if="clinvarData.consequence_categories.truncating > 0"
      class="mb-2 pa-2 rounded"
      style="background-color: rgba(255, 82, 82, 0.1);"
    >
      <div class="d-flex align-center">
        <v-icon size="small" color="error" class="mr-1">mdi-alert</v-icon>
        <strong>{{ clinvarData.consequence_categories.truncating }} Truncating</strong>
      </div>
      <div class="text-caption text-medium-emphasis">
        {{ clinvarData.truncating_percentage }}% of all variants
        <br>
        <span style="font-size: 0.7rem;">
          (nonsense, frameshift, essential splice sites)
        </span>
      </div>
    </div>

    <!-- Other categories -->
    <div class="text-caption">
      <div v-if="clinvarData.consequence_categories.missense > 0">
        <strong>Missense:</strong> {{ clinvarData.consequence_categories.missense }}
        ({{ clinvarData.missense_percentage }}%)
      </div>
      <div v-if="clinvarData.consequence_categories.synonymous > 0">
        <strong>Synonymous:</strong> {{ clinvarData.consequence_categories.synonymous }}
        ({{ clinvarData.synonymous_percentage }}%)
      </div>
      <div v-if="clinvarData.consequence_categories.inframe > 0">
        <strong>In-frame:</strong> {{ clinvarData.consequence_categories.inframe }}
      </div>
      <div v-if="clinvarData.consequence_categories.splice_region > 0">
        <strong>Splice region:</strong> {{ clinvarData.consequence_categories.splice_region }}
      </div>
    </div>

    <!-- Top specific consequences -->
    <div v-if="clinvarData.top_molecular_consequences?.length" class="mt-2">
      <v-divider class="my-2" />
      <div class="text-caption text-medium-emphasis">Most common:</div>
      <div
        v-for="(cons, idx) in clinvarData.top_molecular_consequences.slice(0, 3)"
        :key="idx"
        class="text-caption"
      >
        • {{ cons.consequence }}: {{ cons.count }}
      </div>
    </div>
  </div>
</v-tooltip>
```

#### Change 3.2: Enhance pathogenic chip tooltip (Line 66)
**Location**: After line 66 (inside pathogenic tooltip content)
**Add**: Consequence breakdown
```vue
<!-- ADD after line 66 (after percentage display) -->
<div v-if="clinvarData.consequence_categories" class="mt-2">
  <v-divider class="my-1" />
  <div class="text-caption">
    <span v-if="clinvarData.consequence_categories.truncating">
      Truncating: {{ clinvarData.consequence_categories.truncating }}<br>
    </span>
    <span v-if="clinvarData.consequence_categories.missense">
      Missense: {{ clinvarData.consequence_categories.missense }}
    </span>
  </div>
</div>
```

## Testing (2 new files)

### 4. `/backend/tests/test_clinvar_consequences.py` (NEW FILE)
```python
"""Test ClinVar molecular consequences extraction and categorization."""

import pytest
from unittest.mock import Mock, patch
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource


class TestClinVarConsequences:
    """Test molecular consequence handling."""

    def test_parse_variant_with_consequences(self):
        """Test extraction of molecular_consequence_list."""
        clinvar = ClinVarAnnotationSource(Mock())

        variant_data = {
            "uid": "12345",
            "obj_type": "single nucleotide variant",
            "molecular_consequence_list": ["frameshift variant", "nonsense"]
        }

        result = clinvar._parse_variant(variant_data)

        assert result["molecular_consequences"] == ["frameshift variant", "nonsense"]
        assert result["variant_type"] == "single nucleotide variant"

    def test_parse_variant_without_consequences(self):
        """Test graceful handling when molecular_consequence_list is missing."""
        clinvar = ClinVarAnnotationSource(Mock())

        variant_data = {
            "uid": "12345",
            "obj_type": "single nucleotide variant"
        }

        result = clinvar._parse_variant(variant_data)

        assert result["molecular_consequences"] == []

    def test_aggregate_variants_categorization(self):
        """Test correct categorization of consequences."""
        clinvar = ClinVarAnnotationSource(Mock())

        variants = [
            {"molecular_consequences": ["frameshift variant"], "classification": "pathogenic"},
            {"molecular_consequences": ["nonsense"], "classification": "pathogenic"},
            {"molecular_consequences": ["missense variant"], "classification": "pathogenic"},
            {"molecular_consequences": ["synonymous variant"], "classification": "benign"},
            {"molecular_consequences": ["splice donor variant"], "classification": "pathogenic"},
        ]

        stats = clinvar._aggregate_variants(variants)

        # Check counts
        assert stats["consequence_categories"]["truncating"] == 3  # frameshift, nonsense, splice donor
        assert stats["consequence_categories"]["missense"] == 1
        assert stats["consequence_categories"]["synonymous"] == 1

        # Check percentages
        assert stats["truncating_percentage"] == 60.0  # 3/5
        assert stats["missense_percentage"] == 20.0    # 1/5
        assert stats["synonymous_percentage"] == 20.0  # 1/5

        # Check top consequences
        assert len(stats["top_molecular_consequences"]) <= 10

    def test_aggregate_variants_empty_consequences(self):
        """Test aggregation when no consequences are provided."""
        clinvar = ClinVarAnnotationSource(Mock())

        variants = [
            {"molecular_consequences": [], "classification": "pathogenic"},
            {"classification": "benign"},  # Missing field entirely
        ]

        stats = clinvar._aggregate_variants(variants)

        # All categories should be 0
        assert all(count == 0 for count in stats["consequence_categories"].values())
        assert stats["truncating_percentage"] == 0
```

### 5. `/backend/scripts/backfill_clinvar_consequences.py` (NEW FILE)
```python
#!/usr/bin/env python
"""Backfill molecular consequences for existing ClinVar annotations."""

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.cache_service import get_cache_service
from app.core.logging import get_logger
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.models.gene import Gene
from app.models.gene_annotation import GeneAnnotation

logger = get_logger(__name__)


async def backfill_molecular_consequences():
    """Re-fetch ClinVar data to get molecular consequences."""
    engine = create_engine(settings.DATABASE_URL)

    with Session(engine) as db:
        # Initialize services
        cache_service = get_cache_service(db)
        clinvar_source = ClinVarAnnotationSource(db)

        # Clear ClinVar cache to ensure fresh data
        await cache_service.clear_pattern("annotations:clinvar:*")
        logger.sync_info("Cleared ClinVar cache")

        # Find genes that have ClinVar data but no consequences
        genes_to_update = db.execute(text("""
            SELECT DISTINCT g.*
            FROM genes g
            JOIN gene_annotations ga ON ga.gene_id = g.id
            WHERE ga.source_id = (SELECT id FROM annotation_sources WHERE name = 'clinvar')
            AND ga.annotations->>'total_variants' IS NOT NULL
            AND ga.annotations->>'total_variants' != '0'
            AND NOT ga.annotations ? 'molecular_consequences'
            LIMIT 100  -- Process in batches
        """)).fetchall()

        logger.sync_info(f"Found {len(genes_to_update)} genes to update")

        # Process with rate limiting
        semaphore = asyncio.Semaphore(2)  # Max 2 concurrent requests

        async def process_gene(gene_row):
            async with semaphore:
                try:
                    # Create Gene object from row
                    gene = Gene(
                        id=gene_row.id,
                        approved_symbol=gene_row.approved_symbol,
                        hgnc_id=gene_row.hgnc_id
                    )

                    # Fetch updated annotation
                    annotation = await clinvar_source.fetch_annotation(gene)

                    if annotation and "molecular_consequences" in annotation:
                        logger.sync_info(
                            f"Updated {gene.approved_symbol}",
                            truncating=annotation["consequence_categories"].get("truncating", 0),
                            total=annotation["total_variants"]
                        )

                    # Rate limit
                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.sync_error(
                        f"Failed to update {gene_row.approved_symbol}",
                        error=str(e)
                    )

        # Process all genes
        tasks = [process_gene(gene) for gene in genes_to_update]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        updated_count = db.execute(text("""
            SELECT COUNT(*)
            FROM gene_annotations ga
            WHERE ga.source_id = (SELECT id FROM annotation_sources WHERE name = 'clinvar')
            AND ga.annotations ? 'molecular_consequences'
        """)).scalar()

        logger.sync_info(f"Backfill complete. {updated_count} genes now have molecular consequences")


if __name__ == "__main__":
    asyncio.run(backfill_molecular_consequences())
```

## Verification Steps

### Test Commands
```bash
# 1. Run unit tests
cd backend && uv run pytest tests/test_clinvar_consequences.py -v

# 2. Test single gene manually
cd backend && uv run python -c "
import asyncio
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource
from app.models.gene import Gene
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.core.config import settings

async def test_gene():
    engine = create_engine(settings.DATABASE_URL)
    with Session(engine) as db:
        clinvar = ClinVarAnnotationSource(db)
        gene = db.query(Gene).filter_by(approved_symbol='DMD').first()
        result = await clinvar.fetch_annotation(gene)
        if result and 'molecular_consequences' in result:
            print(f'DMD consequences: {result[\"consequence_categories\"]}')
            print(f'Truncating: {result[\"truncating_percentage\"]}%')
        else:
            print('No molecular consequences found')

asyncio.run(test_gene())
"

# 3. Run backfill script (after implementation)
cd backend && uv run python scripts/backfill_clinvar_consequences.py
```

### Database Verification
```sql
-- Check if molecular consequences are being stored
SELECT
    g.approved_symbol,
    ga.annotations->'consequence_categories' as categories,
    ga.annotations->'truncating_percentage' as truncating_pct
FROM gene_annotations ga
JOIN genes g ON g.id = ga.gene_id
WHERE ga.source_id = (SELECT id FROM annotation_sources WHERE name = 'clinvar')
AND ga.annotations ? 'molecular_consequences'
LIMIT 5;
```

## Implementation Order

1. **Backend changes first** (clinvar.py modifications)
2. **Test backend manually** with single gene
3. **Add unit tests** and verify they pass
4. **Frontend changes** (ClinVarVariants.vue)
5. **Test in browser** with known genes
6. **Run backfill script** for existing data
7. **Final verification** across multiple genes

## Time Estimate
- Backend implementation: 1-2 hours
- Testing & debugging: 1 hour
- Frontend implementation: 30 minutes
- Backfill existing data: 1-2 hours
- **Total: 3.5-5.5 hours**

## Risk Mitigation
- All new fields are optional (won't break existing code)
- Graceful fallbacks for missing data
- Rate limiting on backfill to avoid API issues
- Can be rolled back by simply not displaying new fields