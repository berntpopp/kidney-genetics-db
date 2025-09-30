# GenCC Scoring System Refactor - Implementation TODO

## Overview
Replace the over-engineered GenCC scoring formula with simple MAX() approach using unified weights across all classification sources.

**Estimated Time**: 2-3 hours
**Risk Level**: Low (view-only changes)
**Testing Required**: Yes - compare before/after scores for validation

## File Changes Required

### 1. Fix GenCC Formula - `backend/app/db/views.py`

#### Change 1A: Replace Complex GenCC Formula (Lines 55-94)

**Current Code (Lines 55-94):**
```sql
WITH gencc_weighted AS (
    SELECT ge.id AS evidence_id,
        -- Complex 3-component formula with RMS, count bonus, etc.
        CASE
            WHEN jsonb_array_length(ge.evidence_data -> 'classifications'::text) > 0 THEN
                (0.5 * (sum(power(
                    CASE
                        WHEN lower(elem.value::text) = '"definitive"'::text THEN 1.0
                        -- ... etc
```

**Replace With:**
```sql
WITH gencc_weighted AS (
    SELECT ge.id AS evidence_id,
        g.id AS gene_id,
        g.approved_symbol,
        ge.source_name,
        -- Simple MAX approach - take the best classification
        (SELECT MAX(
            CASE lower(replace(elem.value::text, ' ', '_'))
                WHEN '"definitive"' THEN 1.0
                WHEN '"strong"' THEN 0.8
                WHEN '"moderate"' THEN 0.6
                WHEN '"supportive"' THEN 0.5
                WHEN '"limited"' THEN 0.4
                WHEN '"disputed_evidence"' THEN 0.2
                WHEN '"no_known_disease_relationship"' THEN 0.0
                ELSE 0.0  -- Unknown = no evidence
            END
        ) FROM jsonb_array_elements(ge.evidence_data -> 'classifications') elem
        ) AS classification_weight
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    WHERE ge.source_name::text = 'GenCC'::text
)
```

#### Change 1B: Fix ClinGen Weights (Lines 101-127)

**Current Code (Lines 103-111 and 113-121):**
```sql
CASE (ge.evidence_data -> 'classifications'::text) ->> 0
    WHEN 'Definitive'::text THEN 1.0
    WHEN 'Strong'::text THEN 0.8
    WHEN 'Moderate'::text THEN 0.6
    WHEN 'Limited'::text THEN 0.4
    WHEN 'Disputed'::text THEN 0.2
    WHEN 'Refuted'::text THEN 0.1  -- WRONG!
    ELSE 0.3  -- WRONG!
END
```

**Replace Both CASE Blocks With:**
```sql
CASE
    WHEN 'Definitive'::text THEN 1.0
    WHEN 'Strong'::text THEN 0.8
    WHEN 'Moderate'::text THEN 0.6
    WHEN 'Limited'::text THEN 0.4
    WHEN 'Disputed'::text THEN 0.2
    WHEN 'No Known Disease Relationship'::text THEN 0.0
    WHEN 'No Known Disease Relationship*'::text THEN 0.0
    ELSE 0.0  -- Unknown = no evidence
END
```

**Line 122 - Change:**
```sql
ELSE 0.3  -- Current
```
**To:**
```sql
ELSE 0.0  -- Unknown = no evidence
```

### 2. Remove PERCENT_RANK from GenCC - `backend/app/db/views.py`

#### Change 2A: Simplify evidence_normalized_scores View (Lines 166-203)

**Current Code (Lines 169-178, 194-200):**
```sql
WITH gencc_percentiles AS (
    SELECT ...
        percent_rank() OVER (ORDER BY classification_weight) AS percentile_score
    FROM evidence_classification_weights
    WHERE source_name::text = 'GenCC'::text
)
-- ... later ...
SELECT gencc_percentiles.evidence_id,
    ...
    gencc_percentiles.percentile_score AS normalized_score
FROM gencc_percentiles
```

**Replace With:**
```sql
-- Remove the gencc_percentiles CTE entirely
-- In the final SELECT, change GenCC part to:
UNION ALL
SELECT evidence_classification_weights.evidence_id,
    evidence_classification_weights.gene_id,
    evidence_classification_weights.approved_symbol,
    evidence_classification_weights.source_name,
    evidence_classification_weights.classification_weight AS normalized_score
FROM evidence_classification_weights
WHERE evidence_classification_weights.source_name::text = 'GenCC'::text
```

**Specific Line Changes:**
- **Delete lines 169-178** (gencc_percentiles CTE)
- **Replace lines 194-200** with the simpler SELECT above

### 3. Add Logging for Count-Based Sources - `backend/app/db/views.py`

#### Change 3A: Add Logarithmic Transform to evidence_count_percentiles (Lines 149-162)

**Current Code (Line 157):**
```sql
percent_rank() OVER (PARTITION BY source_name ORDER BY source_count) AS percentile_score
```

**Replace With:**
```sql
percent_rank() OVER (
    PARTITION BY source_name
    ORDER BY LN(1.0 + source_count::numeric)
) AS percentile_score
```

## Testing Plan

### 1. Create Backup Views Before Changes
```sql
-- Run in psql before making changes
CREATE VIEW evidence_classification_weights_backup AS
SELECT * FROM evidence_classification_weights;

CREATE VIEW evidence_normalized_scores_backup AS
SELECT * FROM evidence_normalized_scores;

CREATE VIEW gene_scores_backup AS
SELECT * FROM gene_scores;
```

### 2. Validation Queries

#### Query A: Compare GenCC Scores Before/After
```sql
WITH comparison AS (
    SELECT
        g.approved_symbol,
        old.classification_weight as old_weight,
        new.classification_weight as new_weight,
        ABS(old.classification_weight - new.classification_weight) as difference
    FROM genes g
    JOIN evidence_classification_weights_backup old ON old.gene_id = g.id
    JOIN evidence_classification_weights new ON new.gene_id = g.id
    WHERE old.source_name = 'GenCC' AND new.source_name = 'GenCC'
)
SELECT * FROM comparison
ORDER BY difference DESC
LIMIT 20;
```

#### Query B: Check Score Distribution
```sql
-- Should show full [0, 1] range usage
SELECT
    source_name,
    MIN(classification_weight) as min_score,
    MAX(classification_weight) as max_score,
    AVG(classification_weight) as avg_score,
    STDDEV(classification_weight) as std_dev
FROM evidence_classification_weights
WHERE source_name IN ('GenCC', 'ClinGen')
GROUP BY source_name;
```

#### Query C: Verify No Unknown Disease Relationships Score > 0
```sql
-- Should return empty set
SELECT g.approved_symbol, ge.evidence_data, ecw.classification_weight
FROM gene_evidence ge
JOIN genes g ON g.id = ge.gene_id
JOIN evidence_classification_weights ecw ON ecw.evidence_id = ge.id
WHERE ge.source_name = 'GenCC'
AND ge.evidence_data::text ILIKE '%no_known_disease%'
AND ecw.classification_weight > 0;
```

### 3. Rollback Plan
```sql
-- If issues found, restore original views
DROP VIEW IF EXISTS evidence_classification_weights CASCADE;
CREATE VIEW evidence_classification_weights AS
SELECT * FROM evidence_classification_weights_backup;

-- Repeat for other views
```

## Implementation Steps

1. **Backup Current State**
   ```bash
   # Create database backup
   make db-backup-full

   # Save current view definitions
   psql -U kidney_user -d kidney_genetics -c "\d+ evidence_classification_weights" > views_backup.sql
   ```

2. **Apply Changes**
   - Open `backend/app/db/views.py`
   - Make changes as specified above
   - Save file

3. **Update Database Views**
   ```bash
   # Recreate views with new definitions
   cd backend
   alembic revision --autogenerate -m "Simplify GenCC scoring formula"
   alembic upgrade head
   ```

4. **Run Validation**
   - Execute all validation queries
   - Compare score distributions
   - Check top 100 genes remain relatively stable

5. **Document Changes**
   ```bash
   # Update migration documentation
   echo "GenCC formula simplified from complex 3-component to MAX(classification)" >> migrations.log
   ```

## Expected Outcomes

### Before
- GenCC: 34 unique scores clustered in 0.28-0.85 range
- Complex formula producing narrow distribution
- "No Known Disease Relationship" getting non-zero scores

### After
- GenCC: 7 distinct scores (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0)
- Full [0, 1] range utilization
- "No Known Disease Relationship" = 0.0
- Consistent weights across GenCC and ClinGen

## Success Criteria

- [ ] GenCC uses simple MAX() instead of complex formula
- [ ] Same classification terms have same weights across sources
- [ ] "No Known Disease Relationship" maps to 0.0
- [ ] Unknown classifications default to 0.0, not 0.3
- [ ] Count-based sources use logarithmic transform
- [ ] No PERCENT_RANK applied to GenCC scores
- [ ] Total SQL reduced from ~200 lines to ~100 lines

## Code Review Checklist

- [ ] All CASE statements use consistent weights
- [ ] No ELSE 0.3 anywhere (should be ELSE 0.0)
- [ ] GenCC formula is single MAX() operation
- [ ] ClinGen weights match GenCC weights
- [ ] PERCENT_RANK removed from GenCC in evidence_normalized_scores
- [ ] Logarithmic transform added to count-based sources

## Notes for PostgreSQL Performance

- The simplified MAX() approach will be faster than the complex formula
- Consider adding index on `(source_name, gene_id)` if not exists
- View recreation should take < 1 second
- No data migration required - only view definitions change

## Python Code Changes Required

**None!** All changes are in PostgreSQL views. The Python code reads from these views and will automatically get the new scores.

## Frontend Changes Required

**None!** The API returns the same structure, just with better score distributions.