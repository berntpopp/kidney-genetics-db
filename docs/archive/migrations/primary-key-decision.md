# Primary Key Strategy Decision Document
## Date: 2025-09-26
## Decision: KEEP BIGINT/INTEGER (Don't Change to UUID)

## Executive Summary
Based on comprehensive research and the specific needs of the Kidney Genetics Database, the recommendation is to **KEEP the current INTEGER/BIGINT strategy** rather than switching to UUIDs.

---

## Key Findings from Research

### Performance Comparison (2024 Data)
| Data Type | Insert Time (1M rows) | Storage Size | Join Performance |
|-----------|----------------------|--------------|------------------|
| INTEGER   | ~250 sec | 4 bytes | Fastest |
| BIGINT    | ~290 sec | 8 bytes | Fast |
| UUID v7   | ~290 sec | 16 bytes | Slower |
| UUID v4   | ~375 sec | 16 bytes | Slowest |
| Text UUID | ~410 sec | 36+ bytes | Terrible |

### Critical Insights
1. **BIGINT performance matches UUID v7** for inserts
2. **UUIDs are 2x-4x larger** than integers
3. **Join performance degrades significantly** with UUIDs
4. **Random UUIDs (v4) cause index fragmentation**

---

## Why NOT to Switch to UUID

### 1. **No Distributed System Requirements**
- Single PostgreSQL instance
- No need for globally unique IDs across systems
- IDs generated within the database

### 2. **Performance Penalties**
```
UUID downsides:
- 16 bytes vs 8 bytes (2x storage)
- Slower JOINs (comparing 16 bytes vs 8 bytes)
- Index bloat (larger keys = bigger indexes)
- Poor cache utilization (larger data = less fits in memory)
```

### 3. **Current Scale Doesn't Justify UUIDs**
- **Genes**: ~30,000 records (INTEGER sufficient)
- **Annotations**: ~500,000 records (INTEGER sufficient)
- **System Logs**: Potentially millions (BIGINT appropriate)
- **Cache**: High turnover (BIGINT appropriate)

### 4. **Rebuild Strategy Eliminates Migration Complexity**
Since you're rebuilding without data preservation:
- No need to preserve existing IDs
- Can start fresh with proper types
- Simpler to keep integer-based approach

---

## Recommended Approach: BIGINT for Everything

### Simplification Strategy
```sql
-- Use BIGINT for ALL tables (uniform approach)
CREATE TABLE genes (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    ...
);

CREATE TABLE users (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    ...
);

-- Benefits:
-- 1. No type mismatches
-- 2. Future-proof (9.2 quintillion max)
-- 3. Consistent foreign keys
-- 4. Simple mental model
```

### Why BIGINT Everywhere?
1. **Future-Proof**: Never worry about overflow
2. **Negligible Cost**: 4 extra bytes per row is trivial
3. **Consistency**: All FKs are same type
4. **No Surprises**: Tables can grow unexpectedly
5. **Modern Standard**: PostgreSQL team recommends it

---

## Migration Strategy (Clean Rebuild)

### Since Data Doesn't Need Preservation:
```bash
# 1. Create backup (for reference only)
make db-backup-full

# 2. Drop existing database
dropdb kidney_genetics_db

# 3. Create fresh database
createdb kidney_genetics_db

# 4. Apply new migration with BIGINT everywhere
alembic upgrade head

# 5. Rebuild data from sources
python -m app.pipeline.rebuild_all

# 6. Verify
python -m app.validate_database
```

### Benefits of Clean Rebuild:
- ✅ No complex migration logic
- ✅ No data transformation needed
- ✅ Clean slate with modern schema
- ✅ Consistent types throughout
- ✅ No legacy baggage

---

## Final Recommendation

### DO:
- ✅ **Use BIGINT for all primary keys** (simplicity + future-proof)
- ✅ **Use GENERATED ALWAYS AS IDENTITY** (modern PostgreSQL 10+)
- ✅ **Clean rebuild** without data preservation
- ✅ **Keep it simple** - don't over-engineer

### DON'T:
- ❌ **Don't use UUID** unless you have distributed requirements
- ❌ **Don't mix INTEGER and BIGINT** - causes confusion
- ❌ **Don't use SERIAL** - use IDENTITY instead
- ❌ **Don't preserve data** - rebuild from sources

---

## Implementation Checklist

1. [ ] Update migration to use BIGINT for ALL tables
2. [ ] Update all models to use BigInteger
3. [ ] Remove INTEGER/BIGINT distinction
4. [ ] Use GENERATED ALWAYS AS IDENTITY
5. [ ] Test clean rebuild process
6. [ ] Document rebuild procedure
7. [ ] Execute clean migration

---

## Performance Expectations

With BIGINT everywhere:
- **Insert Performance**: Optimal
- **Join Performance**: Optimal
- **Storage Overhead**: Minimal (4 bytes extra per row)
- **Index Size**: 8 bytes per key (acceptable)
- **Future Capacity**: 9,223,372,036,854,775,807 rows

---

## Conclusion

**BIGINT is the right choice** for the Kidney Genetics Database:
- Best performance for single-database system
- Simpler than UUID management
- Future-proof capacity
- Industry best practice for PostgreSQL
- Clean rebuild makes migration trivial

The slight storage increase (4 bytes per row) is negligible compared to the benefits of consistency and future-proofing. With ~5,000 genes, the total overhead is just 20KB - completely insignificant.

**Decision: Proceed with BIGINT for all primary keys.**