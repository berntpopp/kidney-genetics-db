# Codebase Review Remediation Design

**Date**: 2026-03-13
**Scope**: Full remediation of all findings from CODEBASE-REVIEW.md + matview bug
**Approach**: Risk-ordered, batch-optimized with maximum parallelization via subagents

---

## Overview

Address all findings across security (S1-S15), performance (P1-P12), maintainability (M1-M14), and best practices (B1-B7) from the comprehensive code review, plus one additional bug (broken `gene_distribution_analysis` materialized view). Work is organized into 3 sequential batches, with maximum parallelization within each batch using isolated git worktrees.

### Execution Strategy: Subagent Parallelization

Each batch contains independent sub-batches that can run in parallel using git worktrees. Sub-batches within a batch touch different files and have no dependencies on each other. Batches themselves are sequential (Batch 2 depends on Batch 1 outputs).

```
Batch 1 (Critical)       Batch 2 (High)           Batch 3 (Medium + Polish)
├── 1A (config/secrets)   ├── 2A (statistics)       ├── 3A (god file split)
├── 1B (SQL safety +      ├── 2B (cache perf)       ├── 3B (query safety)
│    view refresh +        ├── 2C (auth security)    ├── 3C (token storage)
│    matview bug)          ├── 2D (pydantic v2)      ├── 3D (config cleanup)
├── 1C (rate limit)       └── 2E (exceptions)       ├── 3E (security headers)
└── 1D (indexes)                                     ├── 3F (frontend quality)
                                                      └── 3G (cleanup)
     All parallel              All parallel               All parallel
```

### Out of Scope

- Email service for password reset (separate feature)
- CAPTCHA on login (separate feature)
- BFF pattern (overkill for single-service architecture)
- Asymmetric JWT keys (HS256 appropriate for this project)

---

## Batch 1: Critical Security & Stability (~7h)

**Prerequisite**: None
**Parallelization**: All 4 sub-batches run in parallel (no file overlap)

### 1A: Secrets & Config

**Findings**: S1, B6, B7
**Files touched**: `backend/app/core/config.py`, `backend/.env.example`, `backend/tests/conftest.py`, `backend/app/main.py`, `backend/alembic/env.py`, `.pre-commit-config.yaml`, `.github/workflows/gitleaks.yml`, `.github/workflows/ci.yml`, `.gitleaks.toml`

**Changes**:

1. **config.py** — Convert all sensitive fields to `SecretStr` with no defaults:
   - `JWT_SECRET_KEY: SecretStr` (no default)
   - `ADMIN_PASSWORD: SecretStr` (no default)
   - `DATABASE_URL: SecretStr` (no default)
   - `POSTGRES_PASSWORD: SecretStr` (no default — currently `"kidney_pass"` at line 107)
   - `OPENAI_API_KEY: SecretStr | None = None` (optional but still secret when present)
   - Add `field_validator` for `JWT_SECRET_KEY` rejecting values < 32 chars or placeholder strings
   - Add `secrets_dir="/run/secrets"` to `SettingsConfigDict`

2. **Ripple effects** — All usages of `SecretStr` fields must call `.get_secret_value()`. Specific files:
   - `backend/app/core/security.py` — JWT encoding/decoding uses `settings.JWT_SECRET_KEY`
   - `backend/app/core/database.py` (or wherever `create_engine` is called) — uses `settings.DATABASE_URL`
   - `backend/alembic/env.py` — uses `settings.DATABASE_URL` for migrations
   - `backend/tests/conftest.py` — test database URL
   - `backend/app/services/backup_service.py` — uses `settings.POSTGRES_PASSWORD` in subprocess env
   - `backend/app/core/database_init.py` — admin user creation uses `settings.ADMIN_PASSWORD`
   - Grep for all `settings.JWT_SECRET_KEY`, `settings.DATABASE_URL`, `settings.ADMIN_PASSWORD`, `settings.POSTGRES_PASSWORD`, `settings.OPENAI_API_KEY` to find all call sites.

3. **B6**: Replace hardcoded `DEBUG` log level in `main.py` with `settings.LOG_LEVEL` (new field, default `"INFO"`).

4. **B7**: Remove hardcoded test DB URL fallback from `conftest.py`. Require `TEST_DATABASE_URL` env var.

5. **`.env.example`** — Update with clear placeholder values and generation instructions:
   ```bash
   # REQUIRED — Generate with: python -c "import secrets; print(secrets.token_hex(32))"
   JWT_SECRET_KEY=
   # REQUIRED — Set a secure admin password
   ADMIN_PASSWORD=
   # Database connection
   DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   POSTGRES_PASSWORD=
   # Logging level (DEBUG, INFO, WARNING, ERROR)
   LOG_LEVEL=INFO
   ```

6. **Gitleaks** — Add secret scanning:
   - `.pre-commit-config.yaml`: Add gitleaks hook (rev v8.24.2)
   - `.github/workflows/gitleaks.yml`: Secret scanning on push/PR
   - `.gitleaks.toml`: Config with allowlist for `.planning/`, `node_modules/`, `.env.example`, `uv.lock`, `package-lock.json`

7. **CI** — Update `.github/workflows/ci.yml` to use GitHub Secrets for test env vars.

**Verification**: App starts with valid `.env`, fails with clear error without it. `repr(settings)` shows `SecretStr('**********')`. Gitleaks pre-commit blocks commits with secrets. All tests pass with `TEST_DATABASE_URL` set.

### 1B: SQL Safety + View Refresh + Matview Bug

**Findings**: S2, S3, P1, plus `gene_distribution_analysis` bug
**Files touched**: New `backend/app/db/safe_sql.py`, `backend/app/db/registry.py`, `backend/app/db/materialized_views.py`, `backend/app/api/endpoints/gene_annotations.py`, `backend/app/pipeline/annotation_pipeline.py`, `backend/app/pipeline/sources/annotations/base.py`, `backend/app/core/database_init.py`

**Changes**:

1. **Create `backend/app/db/safe_sql.py`**:
   ```python
   import re
   from sqlalchemy import text
   from sqlalchemy.orm import Session

   VALID_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

   def safe_identifier(name: str) -> str:
       if not VALID_IDENTIFIER_RE.match(name):
           raise ValueError(f"Invalid SQL identifier: {name!r}")
       return name

   def refresh_materialized_view(
       session: Session, view_name: str, concurrent: bool = True
   ) -> None:
       name = safe_identifier(view_name)
       clause = "CONCURRENTLY " if concurrent else ""
       session.execute(text(f"REFRESH MATERIALIZED VIEW {clause}{name}"))
       session.commit()

   def drop_materialized_view(session: Session, view_name: str) -> None:
       name = safe_identifier(view_name)
       session.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE"))
       session.commit()

   def get_view_definition(session: Session, view_name: str) -> str | None:
       return session.execute(
           text("SELECT pg_get_viewdef(:name::regclass, true)"),
           {"name": view_name},
       ).scalar()
   ```

2. **Replace all f-string DDL** across 7 locations with `safe_sql` functions.

3. **P1 — Blocking view refresh fix** in `gene_annotations.py` (lines ~581-588):
   ```python
   from starlette.concurrency import run_in_threadpool
   from app.db.safe_sql import refresh_materialized_view

   await run_in_threadpool(refresh_materialized_view, db, view_name, concurrent=True)
   ```
   This fixes both the SQL injection AND the event loop blocking in one change.

4. **Matview bug — `gene_distribution_analysis`** in `materialized_views.py` (lines 88-139):
   Replace `classification` with `evidence_tier` in both the `score_bins` and `source_distribution` CTEs, and in the final `UNION ALL` SELECT. The `gene_scores` view has `evidence_tier` and `evidence_group` columns — no `classification` column exists. This column was likely renamed during development but the matview definition was never updated. Without this fix, `MaterializedViewManager.initialize_all_views()` fails on fresh databases.

**Verification**: All DDL operations work. Invalid identifiers raise `ValueError`. View refresh doesn't block the event loop. `gene_distribution_analysis` matview creates successfully on a fresh database.

### 1C: Runtime Crash Fix

**Finding**: S4
**Files touched**: `backend/app/core/rate_limit.py`

**Change**: Fix the import and call site at lines 36-38.

Current code:
```python
from app.core.security import decode_access_token
payload = decode_access_token(auth_header.split(" ", 1)[1])
```

`decode_access_token` does not exist in `security.py`. The available function is `verify_token(token: str, token_type: str = "access") -> dict[str, Any] | None` (line 116). Fix:
```python
from app.core.security import verify_token
payload = verify_token(auth_header.split(" ", 1)[1], token_type="access")
```

Note: `verify_token` returns `dict[str, Any] | None` (same shape as before — contains `sub`, `role`, etc.), so the downstream `payload["sub"]` and `payload.get("role", "")` calls at lines 39-44 remain valid. The `None` case is already handled by the `if payload and "sub" in payload:` guard.

**Verification**: Rate limiter resolves admin users without crashing. Test with valid and invalid Bearer tokens.

### 1D: Missing Indexes

**Finding**: P3
**Files touched**: New Alembic migration

**Change**: Create migration with 3 indexes:
```sql
CREATE INDEX CONCURRENTLY idx_cache_entries_key_expires
    ON cache_entries(cache_key, expires_at);

CREATE INDEX CONCURRENTLY idx_gene_evidence_gene_source
    ON gene_evidence(gene_id, source_name);

CREATE INDEX CONCURRENTLY idx_cache_entries_namespace
    ON cache_entries(namespace);
```

Note: `CREATE INDEX CONCURRENTLY` cannot run inside a transaction. The Alembic migration must use `op.execute()` outside of the default transactional DDL.

**Verification**: `EXPLAIN ANALYZE` shows index scans instead of sequential scans for cache lookups and gene evidence filtering.

---

## Batch 2: High Priority Performance & Auth (~12h)

**Prerequisite**: Batch 1 merged
**Parallelization**: All 5 sub-batches run in parallel (no file overlap)

### 2A: Statistics Optimization

**Findings**: P2, P5, P7
**Files touched**: `backend/app/crud/statistics.py`

**Changes**:

1. **P2**: The current implementation (lines 115-152) fetches all gene-source mappings once via `array_agg`, then iterates through `combinations()` in Python performing set intersections, with individual DB queries to resolve gene symbols per combination. Replace with single-query bitmask approach:
   ```sql
   WITH gene_sources AS (
       SELECT gene_id,
              SUM(DISTINCT CASE source_name
                  WHEN 'panelapp' THEN 1
                  WHEN 'clingen' THEN 2
                  -- ... map each source to a power of 2
              END) AS source_bitmask
       FROM gene_curations
       GROUP BY gene_id
   )
   SELECT source_bitmask, COUNT(*) AS gene_count
   FROM gene_sources
   GROUP BY source_bitmask;
   ```
   Decode bitmasks in Python for UpSet plot data. One table scan, no exponential combinations.

2. **P5**: Consolidate remaining sequential DB roundtrips into CTEs.

3. **P7**: Bitmask approach eliminates need for `array_agg` on large datasets.

**Verification**: Source overlap endpoint returns same data, measurably faster. Benchmark before/after.

### 2B: Cache Performance

**Findings**: P4, P8, M10
**Files touched**: `backend/app/core/cache_service.py`, `backend/app/api/endpoints/genes.py`

**Changes**:

1. **P4**: Stop writing cache stats to DB on every GET. Add thread-safe `CacheStats` class with in-memory counters (`threading.Lock`). Batch-persist to DB every 100 operations or 60 seconds.

2. **P8**: The manual TTL cache in `genes.py:39-148` has no `threading.Lock` — race conditions under concurrency. Fix by removing it entirely (M10) and replacing with `CacheService`.

3. **M10**: Remove module-level manual TTL cache in `genes.py:39-148`. Replace with `CacheService` calls. Add `threading.Lock` to L1 LRU cache in `CacheService` for thread safety.

**Verification**: Cache hits are 10-15x faster (no DB write per hit). Gene list endpoint uses `CacheService` consistently. No race conditions under concurrent load.

### 2C: Auth Security

**Findings**: S5, S8, S9
**Files touched**: `backend/app/api/endpoints/auth.py`, `backend/app/core/security.py`, `backend/app/models/` (new RefreshToken model), new Alembic migration

**Changes**:

1. **S5**: Opaque refresh tokens with SHA-256 hashing:
   - New `RefreshToken` SQLAlchemy model with `token_hash` (SHA-256, indexed), `family_id` (UUID, indexed), `user_id`, `is_revoked`, `created_at`, `expires_at`
   - `create_opaque_refresh_token()` returns `(raw_token, sha256_hash)`
   - Token rotation on every use with family-based reuse detection (if revoked token presented, invalidate entire family)
   - Alembic migration for `refresh_tokens` table

2. **S8**: Add `@limiter.limit("3/hour")` on password reset request endpoint.

3. **S9**: Remove token logging from password reset (`auth.py:270-273`). Add comment noting email service integration is a separate feature.

**Verification**: Refresh tokens are SHA-256 hashed in DB. Token reuse invalidates entire family. Password reset rate-limited to 3/hour.

### 2D: Pydantic v2 Migration

**Finding**: B1
**Files touched**: `backend/app/schemas/gene.py` (2 occurrences), `backend/app/schemas/releases.py` (1), `backend/app/schemas/gene_staging.py` (2), `backend/app/schemas/auth.py` (1) — 6 total occurrences across 4 files

**Change**: Replace all `class Config: from_attributes = True` with:
```python
from pydantic import ConfigDict
model_config = ConfigDict(from_attributes=True)
```

**Verification**: All schema serialization works. Tests pass. No remaining `class Config:` patterns.

### 2E: Exception Standardization

**Finding**: M2
**Files touched**: `backend/app/api/endpoints/` (multiple), `backend/app/core/exceptions.py` (extend existing), `backend/app/main.py`

**Important context**: `exceptions.py` already exists with a rich domain-specific hierarchy:
- `KidneyGeneticsException` (base)
- `GeneNotFoundError`, `DataSourceError`, `ValidationError`, `ExternalServiceError`
- `DatabaseError`, `PipelineError`, `CacheError`
- `AuthenticationError`, `PermissionDeniedError`, `ResourceConflictError`, `RateLimitExceededError`

**Changes**:

1. **Do NOT replace the existing hierarchy.** The existing domain-specific names (`GeneNotFoundError`, `PermissionDeniedError`) are better than generic alternatives. Instead, extend if any gaps exist.

2. Register global exception handlers in `main.py` that map the existing exception hierarchy to consistent HTTP responses:
   - `GeneNotFoundError` → 404
   - `ValidationError` → 422
   - `AuthenticationError` → 401
   - `PermissionDeniedError` → 403
   - `ResourceConflictError` → 409
   - `KidneyGeneticsException` (catch-all) → 500

3. Replace all raw `HTTPException(status_code=404, detail="...")` raises across endpoints with the appropriate domain exception. Affected files include `gene_annotations.py` (~10 occurrences), `releases.py`, and others.

4. **Note for Batch 3**: Sub-batch 3A (god file split) must preserve the exception changes made here when splitting `gene_annotations.py`.

**Verification**: All error responses follow consistent JSON format with `error_id`, `type`, `message`. Existing tests adapted.

---

## Batch 3: Medium Priority & Polish (~15h)

**Prerequisite**: Batch 2 merged
**Parallelization**: All 7 sub-batches run in parallel

### 3A: God File Split

**Findings**: M1, M4
**Files touched**: `backend/app/api/endpoints/gene_annotations.py` → split into 3 modules, `backend/app/main.py`

**Changes**:

1. Split into:
   - `annotation_retrieval.py` — GET endpoints
   - `annotation_updates.py` — POST/PUT endpoints, view refresh
   - `percentile_management.py` — percentile endpoints

2. **M4**: Extract duplicated evidence transformation logic (currently in both `gene_annotations.py:88-99` and `genes.py:694-711`) to a shared function in `crud/` or a small utility module.

3. Update router registration in `main.py`.

4. **Important**: Preserve the domain exception changes from 2E — all `HTTPException` calls should already be replaced with domain exceptions by this point.

**Verification**: All annotation endpoints work. No import cycles. Tests pass.

### 3B: Query Safety & Pagination

**Findings**: P6, P9, P10, P11
**Files touched**: `backend/app/crud/gene_staging.py`, `backend/app/services/network_analysis_service.py`, `backend/app/crud/statistics.py`, `backend/app/pipeline/annotation_pipeline.py`

**Changes**:

1. **P6**: Add `LIMIT` to unbounded `.all()` queries in `gene_staging.py` (lines 68, 157, 296). Server-enforced `max_limit=10000`.
2. **P9**: Chunked loading in network analysis (5000-row batches instead of loading 50k+ rows at once).
3. **P10**: Increase conservative 500 chunk size in `annotation_pipeline.py:859` based on resource benchmarking (try 1000-2000).
4. **P11**: Add pagination to statistics responses. Summary by default, `?detail=true` for full data.

**Verification**: No unbounded queries. Network analysis handles large datasets without memory spikes.

### 3C: Token Storage & CSRF

**Findings**: S6, S10
**Files touched**: `backend/app/api/endpoints/auth.py`, `frontend/src/api/client.ts`, `frontend/src/stores/auth.ts`

**Changes**:

1. **S6**: Refresh token → HttpOnly cookie (`SameSite=Strict`, `Secure`, `path=/api/auth`). Access token → memory-only Pinia store (not persisted to localStorage, lost on page refresh). Add silent refresh on app init and on 401 responses.
2. **S10**: Add `X-Requested-With` header check on refresh endpoint as lightweight CSRF defense. With `SameSite=Strict` cookies, full CSRF tokens are unnecessary for this SPA architecture.

**Verification**: Tokens not in localStorage. Refresh works via cookie. Cross-site refresh requests blocked.

### 3D: Configuration Cleanup

**Findings**: M3, B3
**Files touched**: New `backend/app/core/constants.py`, multiple files with magic numbers, `backend/app/api/endpoints/client_logs.py`

**Changes**:

1. **M3**: Extract cache TTL magic numbers (300, 3600, 7200, 1800) to `constants.py`. Single source of truth.
2. **B3**: Add try/except with rollback around bare `db.commit()` calls in `client_logs.py:62-65`. Scope limited to `client_logs.py` — other files' commit patterns are handled by their respective sub-batches.

**Verification**: All TTLs sourced from constants. DB sessions not left in bad state on commit failure.

### 3E: Security Headers & CORS

**Findings**: S7, S12
**Files touched**: `backend/app/main.py`, new `backend/app/middleware/security_headers.py`

**Changes**:

1. **S7**: Restrict CORS to specific methods (`GET, POST, PUT, PATCH, DELETE, OPTIONS`) and headers (`Authorization, Content-Type, Accept, X-Request-ID`). Add `max_age=600` for preflight caching.
2. **S12**: Add `SecurityHeadersMiddleware` with `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`, basic CSP for API (`default-src 'none'; frame-ancestors 'none'`).

**Verification**: Security headers present in responses. CORS preflight cached. No regressions in frontend API calls.

### 3F: Frontend Quality

**Findings**: P12, M5, M6, M8, M9, B2, B4, B5
**Files touched**: `frontend/src/components/gene/GeneTable.vue`, `frontend/src/api/client.ts`, multiple Vue components

**Changes**:

1. **P12**: Add `@tanstack/vue-virtual` for gene table row virtualization (~50 visible rows regardless of dataset size).
2. **M5**: Create `useErrorHandler()` composable replacing repeated error handling in 20+ components.
3. **M6**: Add Vitest + Vue Test Utils component tests for critical components (GeneTable, GeneDetail, auth forms).
4. **M8**: Replace `any[]` and `ref<any>` with proper TypeScript interfaces in `EnrichmentTable.vue:33,69`, `GeneDetail.vue:356`, etc.
5. **M9**: Audit response format inconsistency (JSON:API in `genes.py` vs custom in `gene_annotations.py`). Standardize frontend API client to handle both or align backend responses.
6. **B2**: Where backend endpoints return generic `dict[str, Any]` (e.g., `genes.py:249`, `ingestion.py:358`), add typed Pydantic response models to improve FastAPI validation and OpenAPI docs.
7. **B4**: Standardize on `async/await` throughout — remove `.then()` patterns in `AdminDashboard.vue:467`, `GeneTable.vue:518`.
8. **B5**: Strengthen API response typing in `frontend/src/api/client.ts:59` — replace inline type assertions with proper response interfaces.

**Note**: B2 touches backend files (`genes.py`, `ingestion.py`) but only response model annotations — no logic overlap with other sub-batches.

**Verification**: Gene table renders 5000+ rows at 60 FPS. Component tests pass. No TypeScript `any` in modified files. OpenAPI docs show typed responses.

### 3G: Cleanup

**Findings**: M7, M11, M12, M13, M14, S11, S13, S14, S15
**Files touched**: Multiple (small changes across many files)

**Changes**:

1. **M7**: Resolve/remove ~15 TODO comments (create GitHub issues for real work, delete stale ones).
2. **M11**: Remove commented-out delete gene code in `GeneDetail.vue`.
3. **M12**: Remove unused router import in `GeneDetail.vue`.
4. **M13**: Reduce cache hit debug logging to TRACE level.
5. **M14**: Flatten 4-level nesting in `genes.py:352-388` query building.
6. **S11**: Use `.pgpass` or `PGPASSFILE` env var for subprocess DB credentials in `backup_service.py` instead of exposing in process list.
7. **S13**: Already addressed by 1A (test DB URL hardcoded fallback removed).
8. **S14**: Document as future work (CAPTCHA — separate feature). Create GitHub issue.
9. **S15**: Sanitize tracebacks in error logs for production (show full traces only when `LOG_LEVEL=DEBUG`).

**Verification**: No TODOs without linked issues. No unused imports. Clean lint.

---

## Parallelization Map

```
BATCH 1 (all in parallel via worktrees — no file overlap):
  ┌─ Agent 1: 1A (secrets/config/gitleaks)
  │   Files: config.py, .env.example, conftest.py, main.py (LOG_LEVEL only),
  │          alembic/env.py, security.py (.get_secret_value), database.py,
  │          database_init.py (admin password), backup_service.py (POSTGRES_PASSWORD),
  │          .pre-commit-config.yaml, .gitleaks.toml, .github/workflows/
  │
  ├─ Agent 2: 1B (SQL safety + view refresh + matview bug)
  │   Files: safe_sql.py (new), registry.py, materialized_views.py,
  │          gene_annotations.py (view refresh only), annotation_pipeline.py,
  │          annotations/base.py, database_init.py (DDL only)
  │
  ├─ Agent 3: 1C (rate limit fix)
  │   Files: rate_limit.py
  │
  └─ Agent 4: 1D (indexes)
      Files: new Alembic migration only
  └─ Merge all → run tests → commit

BATCH 2 (all in parallel via worktrees — no file overlap):
  ┌─ Agent 1: 2A (statistics optimization)
  │   Files: statistics.py
  │
  ├─ Agent 2: 2B (cache performance)
  │   Files: cache_service.py, genes.py
  │
  ├─ Agent 3: 2C (auth security)
  │   Files: auth.py, security.py (new token functions), models/ (new model),
  │          new Alembic migration
  │
  ├─ Agent 4: 2D (pydantic v2)
  │   Files: schemas/gene.py, schemas/releases.py, schemas/gene_staging.py,
  │          schemas/auth.py
  │
  └─ Agent 5: 2E (exception standardization)
      Files: exceptions.py (extend), main.py (handlers), gene_annotations.py,
             releases.py, other endpoint files with raw HTTPException
  └─ Merge all → run tests → commit

BATCH 3 (all in parallel via worktrees — no file overlap):
  ┌─ Agent 1: 3A (god file split)
  │   Files: gene_annotations.py → 3 new files, main.py (router registration)
  │
  ├─ Agent 2: 3B (query safety + pagination)
  │   Files: gene_staging.py, network_analysis_service.py, statistics.py (pagination),
  │          annotation_pipeline.py (chunk size)
  │
  ├─ Agent 3: 3C (token storage + CSRF)
  │   Files: auth.py (cookie setting), frontend/src/api/client.ts,
  │          frontend/src/stores/auth.ts
  │
  ├─ Agent 4: 3D (config cleanup)
  │   Files: constants.py (new), client_logs.py, files with magic number TTLs
  │
  ├─ Agent 5: 3E (security headers + CORS)
  │   Files: main.py (CORS config), middleware/security_headers.py (new)
  │
  ├─ Agent 6: 3F (frontend quality)
  │   Files: GeneTable.vue, GeneDetail.vue, AdminDashboard.vue, EnrichmentTable.vue,
  │          frontend/src/api/client.ts, frontend/src/composables/ (new),
  │          frontend tests, genes.py + ingestion.py (response models only — B2)
  │
  └─ Agent 7: 3G (cleanup)
      Files: Multiple files (small changes — TODOs, unused imports, logging levels,
             backup_service.py, genes.py:352-388 nesting)
  └─ Merge all → run tests → commit
```

### File Overlap Conflicts to Monitor

| Batch | File | Sub-batches | Resolution |
|-------|------|-------------|------------|
| 1 | `database_init.py` | 1A (admin password), 1B (DDL) | Different sections — no conflict |
| 2 | `security.py` | 2C (new token functions) | Only 2C touches it in Batch 2 |
| 3 | `main.py` | 3A (routers), 3E (CORS/headers) | Different sections — merge carefully |
| 3 | `genes.py` | 3F (response models), 3G (nesting) | Different sections — merge carefully |
| 3 | `auth.py` | 3C (cookies) | Only 3C touches it in Batch 3 |
| 3 | `client.ts` | 3C (cookie auth), 3F (typing) | Merge carefully |
| 3 | `statistics.py` | 3B (pagination) | Only 3B touches it in Batch 3 |

**Total**: 3 sequential rounds, 4-5-7 parallel agents per round.

---

## Success Criteria

1. All security findings (S1-S15) resolved or explicitly documented as out-of-scope (S14)
2. All performance findings (P1-P12) resolved with measurable improvements
3. All maintainability findings (M1-M14) resolved
4. All best practices findings (B1-B7) resolved
5. `gene_distribution_analysis` materialized view creates successfully on fresh DB
6. `make ci` passes (lint + format + tests for both backend and frontend)
7. `make security` passes (bandit + pip-audit + npm-audit + gitleaks)
8. No regressions in existing functionality
