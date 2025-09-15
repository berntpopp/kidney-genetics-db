# Scoring System Simplification Plan

## TL;DR

The current scoring system is over-engineered with unnecessary complexity. This plan simplifies it while improving mathematical soundness.

**Key Problems:**
1. GenCC creates a sophisticated score then destroys it with PERCENT_RANK (idiotic)
2. Information destruction through excessive percentile ranking
3. Unnecessary complexity in aggregation

**Solution:** Remove over-engineering, preserve information, use simple averaging (no weights).

## Problem 1: GenCC Over-Engineering

### Current Insanity
```sql
-- Step 1: Calculate sophisticated weighted score (lines 60-89)
classification_weight =
    0.5 * (RMS of classification values) +
    0.3 * (sqrt(count/5)) +
    0.2 * (proportion of high-confidence)
-- Result: Score between 0.3 and ~0.9

-- Step 2: DESTROY IT ALL with percentile rank
PERCENT_RANK() OVER (ORDER BY classification_weight)
-- Result: Information destroyed, now just ordinal ranking
```

### Why This is Stupid
- The formula ALREADY produces normalized [0,1] scores
- The formula ALREADY accounts for multiple factors
- Applying PERCENT_RANK destroys the careful weighting
- It's like calculating a GPA then converting it to class rank

### Simple Fix
```sql
-- Use UNIFIED weights across ALL classification sources
CREATE OR REPLACE VIEW evidence_classification_weights AS
...
-- GenCC (use MAX, same weights as ClinGen)
WHEN source_name = 'GenCC' THEN
  (SELECT MAX(
    CASE lower(replace(elem.value::text, ' ', '_'))
      WHEN '"definitive"' THEN 1.0
      WHEN '"strong"' THEN 0.8
      WHEN '"moderate"' THEN 0.6
      WHEN '"supportive"' THEN 0.5  -- GenCC-specific (154 occurrences)
      WHEN '"limited"' THEN 0.4
      WHEN '"disputed_evidence"' THEN 0.2  -- GenCC uses this instead of 'disputed'
      WHEN '"no_known_disease_relationship"' THEN 0.0  -- GenCC's version of refuted
      ELSE 0.0  -- Unknown = no evidence, not 0.3!
    END
  ) FROM jsonb_array_elements(evidence_data -> 'classifications') elem)

-- ClinGen (fix to use consistent weights)
WHEN source_name = 'ClinGen' THEN
  CASE classification
    WHEN 'Definitive' THEN 1.0
    WHEN 'Strong' THEN 0.8
    WHEN 'Moderate' THEN 0.6
    WHEN 'Limited' THEN 0.4
    WHEN 'Disputed' THEN 0.2
    WHEN 'No Known Disease Relationship' THEN 0.0
    WHEN 'No Known Disease Relationship*' THEN 0.0  -- ClinGen variant
    ELSE 0.0  -- Unknown = no evidence
  END
...
```

**Key Principles:**
1. Same classification = same weight everywhere
2. Refuted = 0 (it's REFUTED, not "10% relevant")
3. Unknown = 0 (not some magic 0.3)
4. Use MAX() for multi-classification (best evidence wins)

## Problem 2: Source Weights - Keep It Simple

### The Decision: No Weights, Just Sum

After careful consideration, **summing normalized scores is the correct approach**:

```sql
-- Sum of normalized scores (max 1.0 per source)
raw_score = SUM(normalized_score)
percentage_score = SUM(normalized_score) / COUNT(all_possible_sources) * 100
```

### Why Summing is Better Than Averaging

1. **Rewards multiple sources naturally**
   - Gene with 1 source at 1.0 = 20% (not 100%)
   - Gene with 5 sources at 1.0 = 100%
   - This correctly reflects evidence breadth

2. **Each source contributes additively**
   - Each source adds evidence independently
   - More sources = stronger evidence
   - Maximum contribution per source is 1.0

3. **Simplicity without losing information**
   - No arbitrary weights between sources
   - No complex averaging that equalizes single vs multi-source genes
   - Pure additive aggregation

4. **Mathematically intuitive**
   - Total score = sum of individual evidence strengths
   - Percentage = (sum / max_possible) * 100
   - Max possible = dynamically calculated from active sources
   - Automatically adapts when sources are added/removed

## Problem 3: Information Destruction

### Current Issues
All count-based sources use raw `PERCENT_RANK()` which destroys magnitude information:
- 1 vs 10 publications = same difference as 100 vs 1000 publications
- This is mathematically wrong

### Simple Fix
```sql
-- Apply logarithm BEFORE percentile ranking
CREATE OR REPLACE VIEW evidence_count_percentiles AS
SELECT
    evidence_id,
    gene_id,
    approved_symbol,
    source_name,
    source_count,
    PERCENT_RANK() OVER (
        PARTITION BY source_name
        ORDER BY LN(1.0 + source_count)  -- Natural log preserves ratios
    ) AS percentile_score
FROM evidence_source_counts
WHERE source_count > 0;
```

## Simplified Implementation Plan

### Phase 1: Fix GenCC (1 hour)
```sql
-- Remove percentile ranking from GenCC
-- The weighted formula is already good!
UPDATE evidence_normalized_scores view
SET GenCC to use classification_weight directly
```

### Phase 2: Add Log Transform (2 hours)
```sql
-- Fix count-based sources
UPDATE evidence_count_percentiles view
Add LN(1 + count) before PERCENT_RANK
```

### Phase 3: Final Aggregation (1 hour)

**Implementation: Additive Scoring**
```sql
-- Additive aggregation
CREATE OR REPLACE VIEW gene_scores AS
WITH source_scores_per_gene AS (
    SELECT g.id AS gene_id,
           g.approved_symbol,
           g.hgnc_id,
           ces.source_name,
           MAX(ces.normalized_score) AS source_score
    FROM genes g
    INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
    GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
)
SELECT gene_id,
       approved_symbol,
       hgnc_id,
       COUNT(DISTINCT source_name) AS source_count,
       SUM(source_score) AS raw_score,
       -- Sum of scores, scaled to percentage
       SUM(source_score) * 20 AS percentage_score  -- *20 because max 5 sources
FROM source_scores_per_gene
GROUP BY gene_id, approved_symbol, hgnc_id
```

## Why This is Better

### Current System
```
Raw Data → Complex Formula → Percentile Rank → Arbitrary Weights → Final Score
         ↑                 ↑                  ↑
         Good              Destroys Info      Subjective
```

### Simplified System
```
Raw Data → Log Transform → Normalized Score → Simple Average → Final Score
         ↑              ↑                   ↑
         Preserves      Clean               Objective
         Ratios         [0,1]
```

## Success Criteria

- [x] GenCC uses MAX() instead of complex RMS formula (no PERCENT_RANK after)
- [x] Count sources use log transform before percentile
- [x] Additive scoring for final aggregation (sum, not average)
- [x] Total SQL simplified significantly

## Mathematical Principle

Each source provides evidence for P(gene is disease-relevant).
When properly normalized to [0,1], additive scoring reflects total evidence:

- **Count data**: Log transform preserves multiplicative relationships
- **Classification data**: Direct mapping already normalized
- **Aggregation**: Sum of evidence (max 1.0 per source) reflects breadth
- **Scaling**: Divide by max possible (5 sources) for percentage

## Summary

**Implementation Complete:**
1. GenCC uses simple MAX() - no complex RMS, no PERCENT_RANK after
2. Log transform for counts - preserves magnitude relationships
3. Additive scoring - sum of evidence, not average

**Result:**
- Simpler code
- Mathematically sound
- Rewards multi-source evidence properly
- Single-source genes correctly scored lower

**Key Insight:**
Summing normalized scores (not averaging) correctly rewards genes with evidence from multiple sources while keeping single-source genes appropriately lower.