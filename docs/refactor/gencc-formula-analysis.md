# GenCC Formula Analysis - Why It's Over-Engineered Nonsense

## Executive Summary

After analyzing the actual GenCC data, the complex formula is **completely unjustified**. It's a classic case of over-engineering that adds complexity without value.

## The Data Reality

### Actual GenCC Classification Patterns (313 genes)
```
Top 10 patterns:
('Definitive', 'Strong', 'Supportive'): 42 genes
('Limited',): 31 genes
('Strong',): 26 genes
('Supportive',): 23 genes
('Definitive', 'Strong'): 22 genes
('Definitive',): 21 genes
('Strong', 'Supportive'): 19 genes
('Moderate', 'Strong', 'Supportive'): 18 genes
('Moderate',): 16 genes
('Moderate', 'Strong'): 14 genes
```

**Key Observation**: Most genes have only 1-3 classifications, not 10+

## The Current Formula (Nonsense)

```sql
weight =
  0.5 * RMS(classification_values) +           -- Component 1: RMS of values
  0.3 * LEAST(1.0, SQRT(count/5)) +           -- Component 2: Count bonus
  0.2 * (high_confidence_ratio)               -- Component 3: High conf ratio
```

### Why Each Component is Wrong

#### Component 1: RMS (50% weight) - **Mathematically Inappropriate**
RMS (Root Mean Square) is for continuous signals, not categorical data!

**Example of the absurdity:**
- Gene A: ['Definitive'] → RMS = 1.0
- Gene B: ['Strong', 'Strong'] → RMS = 0.8
- Gene C: ['Definitive', 'Limited'] → RMS = √((1.0² + 0.4²)/2) = 0.76

Why would Gene C with both strong and weak evidence score lower than Gene B with duplicate evidence?

#### Component 2: Count Bonus (30% weight) - **Rewards Quantity Over Quality**
```
SQRT(count/5)
```
This gives bonus points just for having MORE classifications, even if they're weak.

**Example:**
- Gene with 1 'Definitive' → count_bonus = √(1/5) = 0.45
- Gene with 5 'Limited' → count_bonus = √(5/5) = 1.0

The gene with 5 weak classifications gets a higher bonus!

#### Component 3: High Confidence Ratio (20% weight) - **The Only Sensible Part**
This is actually reasonable - it measures the proportion of high-confidence classifications.

## Output Range Problem

The formula produces scores clustered in 0.33-0.68 range:
```
Sample weights:
ACE: 0.6248
ACTN4: 0.6280
ADAMTS9: 0.4175
AGT: 0.6320
AGTR1: 0.6280
ALG5: 0.6231
ALG6: 0.3342
ALG8: 0.6231
```

Then we apply PERCENT_RANK which destroys even this narrow range!

## What GenCC Should Use Instead

### The ONLY Sensible Approach: Use ClinGen's Weights Everywhere

```sql
-- SAME weights for GenCC, ClinGen, and any future classification source
SELECT MAX(
  CASE classification
    WHEN 'Definitive' THEN 1.0
    WHEN 'Strong' THEN 0.8
    WHEN 'Moderate' THEN 0.6
    WHEN 'Limited' THEN 0.4
    WHEN 'Disputed' THEN 0.2
    WHEN 'Refuted' THEN 0.0  -- NO SCORE! It's REFUTED!
    -- Remove 'Supportive' - it's not in ClinGen, why invent it?
  END
)
```

**Why this is the ONLY correct approach:**
1. **Consistency**: Same classification = same score everywhere
2. **Refuted = 0**: If evidence is refuted, it provides ZERO support
3. **No made-up categories**: If ClinGen doesn't have 'Supportive', don't add it

### Option 2: Average Classification (Balanced)
```sql
SELECT AVG(classification_value)
```
**Rationale**: Considers all evidence equally.

### Option 3: Weighted by Source Count (If You Must Be Fancy)
```sql
SELECT
  0.7 * MAX(classification_value) +  -- Best evidence matters most
  0.3 * AVG(classification_value)     -- But consider consensus
```

## Comparison with Other Sources

### ClinGen (Simple and Effective)
- Direct mapping: 'Definitive' → 1.0, 'Strong' → 0.8, etc.
- No complex formula
- Works perfectly

### PanelApp (Count-Based)
- Uses panel count with percentile ranking
- Simple, interpretable

## The Mathematical Truth

For categorical ordinal data (like classifications), appropriate measures are:
- **Mode** (most common)
- **Median** (middle value)
- **Maximum** (best evidence)
- **Minimum** (worst evidence)

NOT appropriate:
- **RMS** (for continuous signals)
- **Quadratic means** (for physics/engineering)
- **Complex weighted formulas** (when you have 1-3 data points)

## Recommendation

**Replace the entire GenCC formula with:**

```sql
-- UNIFIED approach - EXACTLY like ClinGen
CREATE OR REPLACE VIEW evidence_classification_weights AS
...
WHEN source_name = 'GenCC' THEN
  (SELECT MAX(
    CASE lower(elem.value::text)
      WHEN '"definitive"' THEN 1.0
      WHEN '"strong"' THEN 0.8
      WHEN '"moderate"' THEN 0.6
      WHEN '"limited"' THEN 0.4
      WHEN '"disputed"' THEN 0.2
      WHEN '"refuted"' THEN 0.0
      WHEN '"supportive"' THEN 0.5  -- OK, GenCC has this extra one
      ELSE 0.0  -- ELSE should be 0! Unknown = no evidence!
    END
  ) FROM jsonb_array_elements(evidence_data -> 'classifications') elem)
...
```

**Why ELSE 0.3 is STUPID:**
- What does 0.3 even mean? "30% disease relevant"?
- If we don't recognize the classification, it's NOT evidence
- Default should be 0 (no evidence), not some arbitrary number

**Benefits:**
- 90% less code
- Actually makes sense
- Uses full [0,1] range
- Interpretable
- No information destruction

## Conclusion

The GenCC formula is a textbook example of **over-engineering**:
1. Uses inappropriate mathematical operations (RMS for categories)
2. Rewards quantity over quality
3. Produces narrow output range (0.33-0.68)
4. Then destroys it all with PERCENT_RANK

It's like calculating the RMS of ZIP codes - mathematically possible but conceptually nonsensical.

**Use MAX(classification) and move on.**