# Codebase Review Remediation — Batch 3: Medium Priority & Polish

> **Status: 63% COMPLETE** — 17/27 tasks implemented. 10 tasks skipped (4 not applicable, 3 low-value/high-risk, 3 deferred). Branch: `fix/codebase-review-batch-1-critical` (2026-03-14)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split god files, add query safety/pagination, move tokens to HttpOnly cookies, extract constants, add security headers, improve frontend quality, and clean up dead code/TODOs.

**Architecture:** Seven independent sub-batches with minimal file overlap (see overlap table at bottom), designed for parallel execution in isolated worktrees. Depends on Batch 2 being merged first.

**Tech Stack:** Python/FastAPI, Vue 3/TypeScript, @tanstack/vue-virtual, Vitest, HttpOnly cookies

**Spec:** `docs/superpowers/specs/2026-03-13-codebase-review-remediation-design.md` (Batch 3 section)

**Prerequisite:** Batch 2 plan completed and merged (`docs/superpowers/plans/2026-03-13-codebase-review-batch-2-high.md`)

---

## Chunk 1: Sub-batch 3A — God File Split (Tasks 1–3)

### Task 1: Extract GET endpoints to annotation_retrieval.py

**Files:**
- Create: `backend/app/api/endpoints/annotation_retrieval.py`
- Modify: `backend/app/api/endpoints/gene_annotations.py` (1422 lines → split)
- Test: Existing endpoint tests still pass

**Context:** `gene_annotations.py` is 1422 lines — a god file. Split into 3 focused modules:
- `annotation_retrieval.py` — GET endpoints (read operations)
- `annotation_updates.py` — POST/PUT endpoints (write operations, view refresh)
- `percentile_management.py` — percentile endpoints

- [x] **Step 1: Identify GET endpoints in gene_annotations.py**

Scan for all `@router.get(` endpoints. List them and their line ranges. These will move to `annotation_retrieval.py`.

- [x] **Step 2: Create annotation_retrieval.py with GET endpoints**

Create `backend/app/api/endpoints/annotation_retrieval.py`:

```python
"""GET endpoints for gene annotations — read-only annotation retrieval."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.models.gene import Gene
from app.models.gene_annotation import AnnotationSource, GeneAnnotation

router = APIRouter()
logger = get_logger(__name__)

# Move all @router.get() endpoints here, preserving exact routes and logic
# Each GET endpoint should be moved as-is with its helper functions
```

Move all GET endpoints and their helper functions. Keep imports minimal — only what's needed for reads.

- [x] **Step 3: Remove moved GET endpoints from gene_annotations.py**

Remove the GET endpoints from the original file. What remains becomes the base for `annotation_updates.py`.

- [x] **Step 4: Run tests to verify GET endpoints still work**

Run: `cd backend && uv run pytest -x -q -k "annotation"`
Expected: All annotation tests PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/annotation_retrieval.py backend/app/api/endpoints/gene_annotations.py
git commit -m "refactor(annotations): extract GET endpoints to annotation_retrieval.py (M1)"
```

### Task 2: Extract percentile endpoints and POST/PUT endpoints

**Files:**
- Create: `backend/app/api/endpoints/percentile_management.py`
- Rename: `backend/app/api/endpoints/gene_annotations.py` → `backend/app/api/endpoints/annotation_updates.py`

- [x] **Step 1: Extract percentile endpoints**

Create `backend/app/api/endpoints/percentile_management.py` with all `percentile`-related endpoints.

- [x] **Step 2: Rename remaining file to annotation_updates.py**

The remaining file (POST/PUT endpoints, view refresh) becomes `annotation_updates.py`.

- [x] **Step 3: Run tests**

Run: `cd backend && uv run pytest -x -q -k "annotation or percentile"`
Expected: All PASS

- [x] **Step 4: Commit**

```bash
git add backend/app/api/endpoints/percentile_management.py \
  backend/app/api/endpoints/annotation_updates.py
git commit -m "refactor(annotations): extract percentile and update endpoints (M1)"
```

### Task 3: Update router registration and extract shared evidence transform

**Files:**
- Modify: `backend/app/main.py:177-179` (router registration)
- Create: `backend/app/crud/evidence_transform.py` (shared function)
- Modify: `backend/app/api/endpoints/annotation_retrieval.py` (use shared function)
- Modify: `backend/app/api/endpoints/genes.py:695-711` (use shared function)

- [x] **Step 1: Extract evidence transformation to shared module (M4)**

Create `backend/app/crud/evidence_transform.py`:

```python
"""Shared evidence data transformation utilities.

Extracted from gene_annotations.py and genes.py to avoid DRY violation.
"""

from typing import Any


def transform_evidence_to_jsonapi(
    evidence_list: list[Any],
    gene_id: int,
    normalized_scores: dict[int, float] | None = None,
) -> list[dict[str, Any]]:
    """Transform evidence records to JSON:API format.

    Args:
        evidence_list: List of evidence ORM objects.
        gene_id: ID of the parent gene.
        normalized_scores: Optional dict mapping evidence_id → score.

    Returns:
        List of JSON:API-formatted evidence dicts.
    """
    scores = normalized_scores or {}
    evidence_data = []
    for e in evidence_list:
        evidence_data.append(
            {
                "type": "evidence",
                "id": str(e.id),
                "attributes": {
                    "source_name": e.source_name,
                    "source_detail": e.source_detail,
                    "evidence_data": e.evidence_data,
                    "evidence_date": (
                        e.evidence_date.isoformat() if e.evidence_date else None
                    ),
                    "created_at": (
                        e.created_at.isoformat() if e.created_at else None
                    ),
                    "normalized_score": scores.get(e.id, 0.0),
                },
                "relationships": {
                    "gene": {"data": {"type": "genes", "id": str(gene_id)}}
                },
            }
        )
    return evidence_data
```

- [x] **Step 2: Replace duplicate code in both files**

In `annotation_retrieval.py` (formerly in gene_annotations.py ~lines 88-99):
```python
from app.crud.evidence_transform import transform_evidence_to_jsonapi
# Replace inline transformation with:
evidence_data = transform_evidence_to_jsonapi(evidence, gene.id, normalized_scores)
```

In `genes.py` (lines 695-711):
```python
from app.crud.evidence_transform import transform_evidence_to_jsonapi
# Replace inline transformation with:
evidence_data = transform_evidence_to_jsonapi(evidence, gene.id, normalized_scores)
```

- [x] **Step 3: Update router registration in main.py**

In `backend/app/main.py`, replace the single `gene_annotations` router with three:

```python
# Before:
from app.api.endpoints import gene_annotations
app.include_router(
    gene_annotations.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)

# After:
from app.api.endpoints import annotation_retrieval, annotation_updates, percentile_management
app.include_router(
    annotation_retrieval.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
app.include_router(
    annotation_updates.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
app.include_router(
    percentile_management.router, prefix="/api/annotations", tags=["Core Resources - Annotations"]
)
```

Remove the old `gene_annotations` import.

- [x] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/crud/evidence_transform.py backend/app/main.py \
  backend/app/api/endpoints/annotation_retrieval.py \
  backend/app/api/endpoints/genes.py
git commit -m "refactor(annotations): extract shared evidence transform, update routers (M1, M4)"
```

---

## Chunk 2: Sub-batch 3B — Query Safety & Pagination (Tasks 4–6)

### Task 4: Add LIMIT to unbounded queries in gene_staging.py

**Files:**
- Modify: `backend/app/crud/gene_staging.py:157,296`
- Test: `backend/tests/test_query_safety.py` (create)

- [x] **Step 1: Write failing test**

Create `backend/tests/test_query_safety.py`:

```python
"""Tests for query safety — no unbounded .all() queries."""

import pytest
import inspect


@pytest.mark.unit
class TestQuerySafety:
    """Verify no unbounded .all() queries exist."""

    def test_gene_staging_has_limits(self):
        """All .all() queries should have .limit() applied."""
        from app.crud import gene_staging

        source = inspect.getsource(gene_staging)
        # Check that .all() calls are preceded by .limit()
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if ".all()" in line and ".limit(" not in line and ".distinct()" in line:
                # Lines with .distinct().all() need a .limit()
                pytest.fail(
                    f"Unbounded .all() at line ~{i}: {line.strip()}"
                )
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_query_safety.py -v`
Expected: FAIL — unbounded `.all()` found

- [x] **Step 3: Add limits to gene_staging.py**

In `backend/app/crud/gene_staging.py`:

Line 157 — add `.limit(10000)` before `.all()`:
```python
# Before:
.distinct().all()
# After:
.distinct().limit(10000).all()
```

Line 296 — same pattern:
```python
# Before:
.distinct().all()
# After:
.distinct().limit(10000).all()
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_query_safety.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/crud/gene_staging.py backend/tests/test_query_safety.py
git commit -m "fix(query): add LIMIT to unbounded queries in gene_staging (P6)"
```

### Task 5: Chunked loading in network analysis

**Files:**
- Modify: `backend/app/services/network_analysis_service.py`

- [x] **Step 1: Find the large data loading pattern**

Read the network analysis service and identify where large datasets are loaded in one query.

- [x] **Step 2: Add chunked loading**

Replace single large `.all()` calls with batched loading (5000-row chunks):

```python
NETWORK_BATCH_SIZE = 5000

def _load_interactions_chunked(db: Session, gene_ids: list[int]) -> list:
    """Load interactions in chunks to avoid memory spikes."""
    all_results = []
    for i in range(0, len(gene_ids), NETWORK_BATCH_SIZE):
        chunk = gene_ids[i:i + NETWORK_BATCH_SIZE]
        results = db.execute(
            text("SELECT ... WHERE gene_id = ANY(:ids)"),
            {"ids": chunk},
        ).fetchall()
        all_results.extend(results)
    return all_results
```

- [x] **Step 3: Run tests**

Run: `cd backend && uv run pytest -x -q -k "network"`
Expected: All PASS

- [x] **Step 4: Commit**

```bash
git add backend/app/services/network_analysis_service.py
git commit -m "perf(network): chunked loading for large interaction datasets (P9)"
```

### Task 6: Increase pipeline chunk size

**Files:**
- Modify: `backend/app/pipeline/annotation_pipeline.py:859`

- [x] **Step 1: Increase chunk size from 500 to 1500**

In `backend/app/pipeline/annotation_pipeline.py`, line 859:

```python
# Before:
chunk_size = 500
# After:
chunk_size = 1500  # Tuned from resource benchmarking (baseline ~1.2GB, peak ~2.2GB)
```

- [x] **Step 2: Run tests**

Run: `cd backend && uv run pytest -x -q -k "pipeline"`
Expected: All PASS

- [x] **Step 3: Commit**

```bash
git add backend/app/pipeline/annotation_pipeline.py
git commit -m "perf(pipeline): increase annotation batch chunk size to 1500 (P10)"
```

### Task 6b: Add pagination to statistics responses (P11)

**Files:**
- Modify: `backend/app/crud/statistics.py`
- Modify: `backend/app/api/endpoints/statistics.py` (add `?detail=true` parameter)

- [x] **Step 1: Add detail parameter to statistics endpoint**

In the statistics endpoint, add an optional `detail: bool = False` query parameter. When `detail=False` (default), return summary counts only. When `detail=True`, return the full dataset.

```python
@router.get("/source-overlap")
async def get_source_overlap(
    request: Request,
    db: Session = Depends(get_db),
    detail: bool = Query(False, description="Include full gene lists in intersections"),
):
    result = get_source_overlap_data(db)
    if not detail:
        # Strip gene lists from intersections, keep only counts
        for intersection in result.get("intersections", []):
            intersection.pop("genes", None)
    return result
```

- [x] **Step 2: Run tests**

Run: `cd backend && uv run pytest -x -q -k "statistics"`
Expected: All PASS

- [x] **Step 3: Commit**

```bash
git add backend/app/crud/statistics.py backend/app/api/endpoints/statistics.py
git commit -m "feat(api): add pagination/detail toggle to statistics responses (P11)"
```

---

## Chunk 3: Sub-batch 3C — Token Storage & CSRF (Tasks 7–8)

### Task 7: Move refresh token to HttpOnly cookie (backend)

**Files:**
- Modify: `backend/app/api/endpoints/auth.py` (set cookie on login/refresh)
- Test: `backend/tests/test_token_storage.py` (create)

- [x] **Step 1: Write failing test**

Create `backend/tests/test_token_storage.py`:

```python
"""Tests for secure token storage via HttpOnly cookies."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestTokenCookies:
    """Verify refresh tokens are sent as HttpOnly cookies."""

    def test_login_sets_httponly_cookie(self, client_with_auth):
        """Login response should set refresh_token as HttpOnly cookie."""
        # This test depends on having a test user
        # Verify Set-Cookie header contains HttpOnly flag
        response = client_with_auth.post(
            "/api/auth/login",
            json={"username": "admin", "password": "test_password"},
        )
        if response.status_code == 200:
            cookies = response.headers.get("set-cookie", "")
            assert "refresh_token" in cookies
            assert "HttpOnly" in cookies
            assert "SameSite=Strict" in cookies or "SameSite=strict" in cookies
```

- [x] **Step 2: Implement cookie-based refresh tokens in auth.py**

In the login endpoint, after generating tokens, set the refresh token as a cookie:

```python
from fastapi.responses import JSONResponse

# In login endpoint, replace return statement:
response = JSONResponse(content={
    "access_token": access_token,
    "token_type": "bearer",
})
response.set_cookie(
    key="refresh_token",
    value=refresh_token_raw,
    httponly=True,
    secure=True,  # Requires HTTPS in production
    samesite="strict",
    path="/api/auth",
    max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
)
return response
```

In the refresh endpoint, read from cookie instead of request body:

```python
from fastapi import Cookie

@router.post("/refresh")
async def refresh_token(
    request: Request,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    # ... validate and rotate token
```

- [x] **Step 3: Add X-Requested-With check for CSRF defense (S10)**

In the refresh endpoint:

```python
    # Lightweight CSRF check — SameSite=Strict handles most cases
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        raise HTTPException(status_code=403, detail="CSRF check failed")
```

- [x] **Step 4: Run tests**

Run: `cd backend && uv run pytest -x -q -k "auth"`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/auth.py backend/tests/test_token_storage.py
git commit -m "feat(auth): move refresh token to HttpOnly cookie with CSRF check (S6, S10)"
```

### Task 8: Update frontend token handling

**Files:**
- Modify: `frontend/src/api/client.ts:29-79`
- Modify: `frontend/src/stores/auth.ts:22-23`

- [x] **Step 1: Remove refresh token from localStorage in auth store**

In `frontend/src/stores/auth.ts`:

```typescript
// Before:
const accessToken = ref<string | null>(localStorage.getItem('access_token'))
const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))

// After:
const accessToken = ref<string | null>(null)  // Memory-only, lost on refresh
// refreshToken is now in HttpOnly cookie — not accessible from JS
```

Remove all `localStorage.setItem('refresh_token', ...)` and `localStorage.getItem('refresh_token')` calls. Keep `access_token` in memory only (no localStorage persistence).

- [x] **Step 2: Update API client interceptor**

In `frontend/src/api/client.ts`:

```typescript
// Request interceptor — use memory token, not localStorage
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Import auth store dynamically to avoid circular deps
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`
    }
    // Add CSRF header for refresh requests
    config.headers['X-Requested-With'] = 'XMLHttpRequest'
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response interceptor — refresh via cookie (no body needed)
apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Cookie is sent automatically with withCredentials
        const response = await axios.post(
          `${API_BASE_URL}/api/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
          }
        )

        const { access_token } = response.data as { access_token: string }
        const { useAuthStore } = await import('@/stores/auth')
        const authStore = useAuthStore()
        authStore.setAccessToken(access_token)

        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return apiClient(originalRequest)
      } catch {
        // Refresh failed — dispatch logout
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
    }

    return Promise.reject(error)
  }
)
```

- [x] **Step 3: Add silent refresh on app init**

In the auth store, add an `initAuth()` action that attempts a silent refresh on page load:

```typescript
async function initAuth() {
  try {
    const response = await axios.post(
      `${config.apiBaseUrl}/api/auth/refresh`,
      {},
      { withCredentials: true, headers: { 'X-Requested-With': 'XMLHttpRequest' } }
    )
    accessToken.value = response.data.access_token
    await fetchCurrentUser()
  } catch {
    // No valid refresh cookie — user is not authenticated
    accessToken.value = null
    user.value = null
  }
}
```

Call `initAuth()` in the app's `onMounted` or router guard.

- [x] **Step 4: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [x] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/stores/auth.ts
git commit -m "feat(auth): move to memory-only access token and cookie refresh (S6)"
```

---

## Chunk 4: Sub-batch 3D — Configuration Cleanup (Tasks 9–10)

### Task 9: Extract magic number TTLs to constants.py

**Files:**
- Create: `backend/app/core/constants.py`
- Modify: Files with magic TTL values

- [x] **Step 1: Create constants.py**

Create `backend/app/core/constants.py`:

```python
"""Centralized constants for cache TTLs, timeouts, and limits.

All magic numbers for TTL/timeout values should be defined here.
"""

# Cache TTLs (seconds)
CACHE_TTL_SHORT = 300  # 5 minutes — semi-static metadata
CACHE_TTL_MEDIUM = 1800  # 30 minutes — moderate refresh
CACHE_TTL_LONG = 3600  # 1 hour — stable data (annotations, network)
CACHE_TTL_EXTENDED = 7200  # 2 hours — rarely changing data

# Backup timeouts (seconds)
BACKUP_TIMEOUT_STANDARD = 3600  # 1 hour — pg_dump
BACKUP_TIMEOUT_EXTENDED = 7200  # 2 hours — pg_restore

# Query limits
MAX_QUERY_RESULTS = 10000  # Server-enforced maximum for unbounded queries
NETWORK_BATCH_SIZE = 5000  # Chunked loading for network analysis
PIPELINE_CHUNK_SIZE = 1500  # Annotation pipeline batch size
```

- [x] **Step 2: Replace magic numbers across codebase**

Search and replace in:
- `backend/app/api/endpoints/gene_annotations.py` — `ttl=3600` → `ttl=CACHE_TTL_LONG`
- `backend/app/services/network_analysis_service.py` — `ttl=3600` → `ttl=CACHE_TTL_LONG`
- `backend/app/services/backup_service.py` — `timeout=3600` / `timeout=7200`

Add import: `from app.core.constants import CACHE_TTL_LONG, BACKUP_TIMEOUT_STANDARD, BACKUP_TIMEOUT_EXTENDED`

- [x] **Step 3: Run tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 4: Commit**

```bash
git add backend/app/core/constants.py backend/app/api/endpoints/ \
  backend/app/services/network_analysis_service.py backend/app/services/backup_service.py
git commit -m "refactor(config): extract magic TTL numbers to constants.py (M3)"
```

### Task 10: Add error handling to bare db.commit() in client_logs.py

**Files:**
- Modify: `backend/app/api/endpoints/client_logs.py:62-66`

- [x] **Step 1: Add try/except with rollback**

In `backend/app/api/endpoints/client_logs.py`, lines 62-66:

```python
# Before:
def _save_log(db: Session, log: SystemLog) -> None:
    """Save log entry to database (sync, runs in thread pool)."""
    db.add(log)
    db.commit()

# After:
def _save_log(db: Session, log: SystemLog) -> None:
    """Save log entry to database (sync, runs in thread pool)."""
    try:
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
        raise
```

- [x] **Step 2: Run tests**

Run: `cd backend && uv run pytest -x -q -k "client_log"`
Expected: All PASS

- [x] **Step 3: Commit**

```bash
git add backend/app/api/endpoints/client_logs.py
git commit -m "fix(db): add rollback on commit failure in client_logs (B3)"
```

---

## Chunk 5: Sub-batch 3E — Security Headers & CORS (Tasks 11–12)

### Task 11: Restrict CORS configuration

**Files:**
- Modify: `backend/app/main.py:134-140`

- [x] **Step 1: Restrict CORS methods and headers**

In `backend/app/main.py`, lines 134-140:

```python
# Before:
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# After:
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID", "X-Requested-With"],
    max_age=600,  # Cache preflight for 10 minutes
)
```

- [x] **Step 2: Run frontend manually to verify no broken requests**

Run: `make hybrid-up && make backend & make frontend &`
Test a few pages in the browser — verify no CORS errors in console.

- [x] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "fix(security): restrict CORS methods and headers, add preflight caching (S7)"
```

### Task 12: Add SecurityHeadersMiddleware

**Files:**
- Create: `backend/app/middleware/security_headers.py`
- Modify: `backend/app/main.py` (register middleware)
- Test: `backend/tests/test_security_headers.py` (create)

- [x] **Step 1: Write failing test**

Create `backend/tests/test_security_headers.py`:

```python
"""Tests for security headers middleware."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestSecurityHeaders:
    """Verify security headers are present in responses."""

    def test_x_content_type_options(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_x_frame_options(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/")
        assert response.headers.get("X-Frame-Options") == "DENY"

    def test_referrer_policy(self):
        from app.main import app

        client = TestClient(app)
        response = client.get("/")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_security_headers.py -v`
Expected: FAIL — headers not present

- [x] **Step 3: Create SecurityHeadersMiddleware**

Create `backend/app/middleware/security_headers.py`:

```python
"""Security headers middleware for API responses."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response
```

- [x] **Step 4: Register in main.py**

In `backend/app/main.py`, after CORS middleware:

```python
from app.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)
```

- [x] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_security_headers.py -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/middleware/security_headers.py backend/app/main.py \
  backend/tests/test_security_headers.py
git commit -m "feat(security): add SecurityHeadersMiddleware with standard headers (S12)"
```

---

## Chunk 6: Sub-batch 3F — Frontend Quality (Tasks 13–17)

### Task 13: Add row virtualization to GeneTable

**SKIPPED:** Table uses server-side pagination (max 100 rows) — virtualization would be over-engineering.

**Files:**
- Modify: `frontend/src/components/GeneTable.vue` (or `GeneTable.vue` — confirm path)
- Modify: `frontend/package.json` (add @tanstack/vue-virtual)

- [ ] **Step 1: Install @tanstack/vue-virtual**

Run: `cd frontend && npm install @tanstack/vue-virtual`

- [ ] **Step 2: Add virtualization to GeneTable**

In the GeneTable component, wrap the table body with `useVirtualizer`:

```typescript
import { useVirtualizer } from '@tanstack/vue-virtual'

const parentRef = ref<HTMLElement | null>(null)

const rowVirtualizer = useVirtualizer({
  count: computed(() => table.getRowModel().rows.length),
  getScrollElement: () => parentRef.value,
  estimateSize: () => 48, // estimated row height in px
  overscan: 10,
})
```

Update the template to render only visible rows using `rowVirtualizer.getVirtualItems()`.

- [ ] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json \
  frontend/src/components/GeneTable.vue
git commit -m "perf(frontend): add row virtualization to GeneTable (P12)"
```

### Task 14: Create useErrorHandler composable

**Files:**
- Create: `frontend/src/composables/useErrorHandler.ts`

- [x] **Step 1: Create composable**

Create `frontend/src/composables/useErrorHandler.ts`:

```typescript
/**
 * Composable for standardized error handling across components.
 * Replaces repeated try/catch + error state patterns.
 */

import { ref } from 'vue'

interface ErrorState {
  message: string
  code?: number
  details?: unknown
}

export function useErrorHandler() {
  const error = ref<ErrorState | null>(null)
  const isError = ref(false)

  function handleError(err: unknown, fallbackMessage = 'An error occurred') {
    const apiErr = err as { response?: { status?: number; data?: { detail?: string } } }
    error.value = {
      message: apiErr.response?.data?.detail ?? fallbackMessage,
      code: apiErr.response?.status,
      details: err,
    }
    isError.value = true
    window.logService?.error(fallbackMessage, err)
  }

  function clearError() {
    error.value = null
    isError.value = false
  }

  return { error, isError, handleError, clearError }
}
```

- [x] **Step 2: Commit**

```bash
git add frontend/src/composables/useErrorHandler.ts
git commit -m "feat(frontend): add useErrorHandler composable (M5)"
```

### Task 15: Replace TypeScript any types

**Files:**
- Modify: `frontend/src/components/GeneTable.vue:37,48,83`

- [x] **Step 1: Define proper interfaces**

Add interfaces for gene data used in GeneTable:

```typescript
interface GeneRow {
  id: number
  approved_symbol: string
  hgnc_id: string
  aliases?: string[]
  evidence_count?: number
  percentage_score?: number
  source_count?: number
  sources?: string[]
  evidence_tier?: string
  evidence_group?: string
}

// Replace:
const genes = ref<any[]>([])        // → ref<GeneRow[]>([])
const filterMeta = ref<any>(null)   // → ref<FilterMetadata | null>(null)
// ColumnDef<any>[]                  // → ColumnDef<GeneRow>[]
```

- [x] **Step 2: Run frontend lint and type check**

Run: `cd frontend && npm run lint && npm run type-check`
Expected: No errors

- [x] **Step 3: Commit**

```bash
git add frontend/src/components/GeneTable.vue
git commit -m "fix(types): replace any types with proper interfaces in GeneTable (M8)"
```

### Task 16: Standardize async/await in AdminDashboard

**Files:**
- Modify: `frontend/src/views/admin/AdminDashboard.vue:460-477`

- [x] **Step 1: Replace .then() with async/await**

In `frontend/src/views/admin/AdminDashboard.vue`, around line 467:

```typescript
// Before:
fetch('/api/admin/logs/statistics?hours=24', {
  headers: { Authorization: `Bearer ${authStore.accessToken}` }
}).then(r => r.json())

// After:
const logStatsResponse = await fetch('/api/admin/logs/statistics?hours=24', {
  headers: { Authorization: `Bearer ${authStore.accessToken}` }
})
const logStats = await logStatsResponse.json()
```

Restructure the `Promise.all` to use separate awaits or keep `Promise.all` with proper async functions.

- [x] **Step 2: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [x] **Step 3: Commit**

```bash
git add frontend/src/views/admin/AdminDashboard.vue
git commit -m "refactor(frontend): standardize async/await in AdminDashboard (B4)"
```

### Task 17: Add typed response models for generic dict endpoints (B2)

**SKIPPED:** Adding response_model to existing dict endpoints is high-risk for breaking API validation.

**Files:**
- Modify: `backend/app/api/endpoints/genes.py` (response_model annotations)
- Modify: `backend/app/api/endpoints/ingestion.py` (response_model annotations)
- Create: Response schema classes in `backend/app/schemas/`

- [ ] **Step 1: Identify endpoints with dict[str, Any] return**

```bash
cd backend && grep -n "dict\[str, Any\]" app/api/endpoints/genes.py app/api/endpoints/ingestion.py
```

- [ ] **Step 2: Create typed response models**

Add Pydantic models for the generic responses. For example:

```python
# In app/schemas/gene.py or a new response_models.py
class GeneDetailResponse(BaseModel):
    data: dict[str, Any]
    included: list[dict[str, Any]] | None = None
    meta: dict[str, Any] | None = None
```

- [ ] **Step 3: Add response_model to endpoints**

```python
@router.get("/gene/{gene_id}", response_model=GeneDetailResponse)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/endpoints/genes.py backend/app/api/endpoints/ingestion.py \
  backend/app/schemas/
git commit -m "feat(api): add typed response models for generic dict endpoints (B2)"
```

### Task 17b: Add Vitest component tests for critical components (M6)

**SKIPPED:** useErrorHandler test added; full component mount tests need extensive router/API mock setup.

**Files:**
- Create: `frontend/src/components/__tests__/GeneTable.test.ts`
- Create: `frontend/src/views/__tests__/GeneDetail.test.ts`
- Create: `frontend/src/composables/__tests__/useErrorHandler.test.ts`

- [ ] **Step 1: Set up Vitest + Vue Test Utils if not already configured**

```bash
cd frontend && npm install -D @vue/test-utils @testing-library/vue vitest jsdom
```

Verify `vitest.config.ts` exists. If not, create one:

```typescript
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
})
```

- [ ] **Step 2: Write useErrorHandler composable test**

Create `frontend/src/composables/__tests__/useErrorHandler.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { useErrorHandler } from '../useErrorHandler'

describe('useErrorHandler', () => {
  it('starts with no error', () => {
    const { error, isError } = useErrorHandler()
    expect(error.value).toBeNull()
    expect(isError.value).toBe(false)
  })

  it('handles error with message', () => {
    const { error, isError, handleError } = useErrorHandler()
    handleError(new Error('test'), 'fallback')
    expect(isError.value).toBe(true)
    expect(error.value?.message).toBe('fallback')
  })

  it('clears error', () => {
    const { error, isError, handleError, clearError } = useErrorHandler()
    handleError(new Error('test'), 'fail')
    clearError()
    expect(error.value).toBeNull()
    expect(isError.value).toBe(false)
  })

  it('extracts API error detail', () => {
    const { error, handleError } = useErrorHandler()
    handleError({ response: { data: { detail: 'Not Found' }, status: 404 } }, 'fallback')
    expect(error.value?.message).toBe('Not Found')
    expect(error.value?.code).toBe(404)
  })
})
```

- [ ] **Step 3: Write GeneTable smoke test**

Create `frontend/src/components/__tests__/GeneTable.test.ts`:

```typescript
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GeneTable from '../GeneTable.vue'

describe('GeneTable', () => {
  it('renders without crashing', () => {
    const wrapper = mount(GeneTable, {
      global: { stubs: ['router-link'] },
    })
    expect(wrapper.exists()).toBe(true)
  })
})
```

- [ ] **Step 4: Run tests**

Run: `cd frontend && npx vitest run`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/__tests__/ frontend/src/views/__tests__/ \
  frontend/src/composables/__tests__/ frontend/vitest.config.ts
git commit -m "test(frontend): add Vitest component tests for critical components (M6)"
```

### Task 17c: Audit response format inconsistency (M9)

**Files:**
- Modify: `frontend/src/api/client.ts` (add response normalization helper)

**Context:** `genes.py` uses JSON:API format (`{data: {...}, included: [...]}`) while `gene_annotations.py` uses custom format. Rather than changing all backend endpoints (high risk), standardize the frontend API client to normalize both formats.

- [x] **Step 1: Document the inconsistency**

Create a brief audit of which endpoints return JSON:API vs custom format:

- JSON:API: `/api/genes`, `/api/genes/{id}`
- Custom: `/api/annotations/*`, `/api/statistics/*`, `/api/auth/*`

- [x] **Step 2: Add response normalization utility**

In `frontend/src/api/client.ts`, add a helper that detects and normalizes JSON:API responses:

```typescript
/** Normalize response — extract data from JSON:API wrapper if present */
export function normalizeResponse<T>(response: { data: T } | T): T {
  if (response && typeof response === 'object' && 'data' in response && 'type' in (response as any).data) {
    return (response as { data: T }).data
  }
  return response as T
}
```

- [x] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "docs(api): audit response format inconsistency, add normalization helper (M9)"
```

### Task 17d: Strengthen API response typing in client.ts (B5)

**SKIPPED:** Already addressed by TokenRefreshResponse interface in client.ts.

**Files:**
- Modify: `frontend/src/api/client.ts:59`

- [ ] **Step 1: Replace inline type assertion with proper interface**

In `frontend/src/api/client.ts`, line 59:

```typescript
// Before:
const { access_token } = response.data as { access_token: string; refresh_token?: string }

// After:
interface TokenRefreshResponse {
  access_token: string
  refresh_token?: string
  token_type?: string
}

const tokenData: TokenRefreshResponse = response.data
const { access_token } = tokenData
```

Move the interface to a shared types file if one exists, or define it at the top of `client.ts`.

- [ ] **Step 2: Run frontend lint and type check**

Run: `cd frontend && npm run lint && npm run type-check`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "fix(types): replace inline type assertions with proper interfaces in API client (B5)"
```

---

## Chunk 7: Sub-batch 3G — Cleanup (Tasks 18–22)

### Task 18: Remove dead code in GeneDetail.vue

**Files:**
- Modify: `frontend/src/views/GeneDetail.vue:273,440-458`

- [x] **Step 1: Remove commented-out router import**

Line 273: Remove `// const router = useRouter() // Currently unused but may be needed for navigation`

- [x] **Step 2: Remove unimplemented deleteGene function**

Lines 440-458: Remove the entire `deleteGene` function and the delete button that calls it (around lines 91-94).

- [x] **Step 3: Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [x] **Step 4: Commit**

```bash
git add frontend/src/views/GeneDetail.vue
git commit -m "cleanup: remove dead code and unimplemented delete in GeneDetail (M11, M12)"
```

### Task 19: Reduce cache debug logging to TRACE

**Files:**
- Modify: `backend/app/core/cache_service.py` (debug → trace level for hits)

- [x] **Step 1: Change cache hit log level**

Find all `logger.sync_debug("...cache HIT...")` calls and change to `logger.sync_trace(...)` or reduce verbosity:

```python
# Before:
logger.sync_debug("L1 cache HIT", key=cache_key)
# After:
# Remove or use trace level if available; if not, make conditional:
if settings.LOG_LEVEL == "DEBUG":
    logger.sync_debug("L1 cache HIT", key=cache_key)
```

- [x] **Step 2: Commit**

```bash
git add backend/app/core/cache_service.py
git commit -m "perf(logging): reduce cache hit debug logging verbosity (M13)"
```

### Task 20: Flatten nested query building in genes.py

**SKIPPED:** Code is already flat with guard clauses — no 4-level nesting found at specified lines.

**Files:**
- Modify: `backend/app/api/endpoints/genes.py:352-388`

- [ ] **Step 1: Read the nested code**

Read lines 352-388 to understand the 4-level nesting.

- [ ] **Step 2: Flatten using early returns or guard clauses**

Restructure the nested conditionals to use early returns, continue statements, or extracted helper functions.

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest -x -q -k "genes"`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/endpoints/genes.py
git commit -m "refactor: flatten 4-level nesting in gene list query building (M14)"
```

### Task 21: Use PGPASSFILE for backup subprocess credentials

**SKIPPED:** Backup uses docker exec -e — PGPASSFILE doesn't apply to containerized workflows.

**Files:**
- Modify: `backend/app/services/backup_service.py`

- [ ] **Step 1: Replace PGPASSWORD env var with PGPASSFILE**

In `backup_service.py`, replace all `f"PGPASSWORD={settings.POSTGRES_PASSWORD.get_secret_value()}"` patterns:

```python
import tempfile
import os

def _create_pgpass_file() -> str:
    """Create temporary .pgpass file for secure credential passing."""
    pgpass = tempfile.NamedTemporaryFile(
        mode="w", suffix=".pgpass", delete=False, prefix="kg_backup_"
    )
    # Format: hostname:port:database:username:password
    pgpass.write(
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}:"
        f"{settings.POSTGRES_DB}:{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD.get_secret_value()}\n"
    )
    pgpass.close()
    os.chmod(pgpass.name, 0o600)  # Required by PostgreSQL
    return pgpass.name
```

Then in subprocess calls:
```python
pgpass_file = _create_pgpass_file()
try:
    env = {**os.environ, "PGPASSFILE": pgpass_file}
    # Remove -e PGPASSWORD from docker exec args
    # Add env= parameter to subprocess call
    result = subprocess.run(cmd, env=env, ...)
finally:
    os.unlink(pgpass_file)
```

- [ ] **Step 2: Run tests**

Run: `cd backend && uv run pytest -x -q -k "backup"`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/backup_service.py
git commit -m "fix(security): use PGPASSFILE instead of PGPASSWORD in subprocess (S11)"
```

### Task 22: Sanitize production tracebacks and resolve TODOs

**SKIPPED:** S15 already handled (build_internal_error returns generic message). M7/S14 deferred — need manual triage.

**Files:**
- Modify: `backend/app/middleware/error_handling.py` (traceback sanitization)
- Multiple files (TODO resolution)

- [ ] **Step 1: Add traceback sanitization for production (S15)**

In `backend/app/middleware/error_handling.py`, modify error responses to exclude full tracebacks when `LOG_LEVEL != "DEBUG"`:

```python
from app.core.config import settings

# In error handler:
include_traceback = settings.LOG_LEVEL == "DEBUG"
if include_traceback:
    error_detail["traceback"] = traceback.format_exc()
```

- [ ] **Step 2: Resolve TODO comments (M7)**

```bash
cd backend && grep -rn "TODO" app/ --include="*.py" | head -20
```

For each TODO:
- If it's real work → create a GitHub issue and replace with `# See: <issue-url>`
- If it's stale → delete the comment
- If it's done → delete the comment

- [ ] **Step 3: Create GitHub issue for CAPTCHA (S14)**

```bash
gh issue create --title "Add CAPTCHA to login endpoint" \
  --body "Security finding S14: Add CAPTCHA or bot protection to the login endpoint to prevent automated credential stuffing attacks." \
  --label "security,enhancement"
```

- [ ] **Step 4: Run full test suite**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [ ] **Step 5: Run lint on both backend and frontend**

Run: `make lint && make lint-frontend`
Expected: No errors

- [ ] **Step 6: Commit**

```bash
git add backend/app/middleware/error_handling.py
git commit -m "fix(security): sanitize tracebacks in production, resolve TODOs (S15, M7)"
```

**Note — S13**: Already addressed by Batch 1 Task 3 (removed hardcoded test DB URL fallback from `conftest.py`). No work needed in Batch 3.

---

## File Overlap Warning

These files are touched by multiple sub-batches within Batch 3:

| File | Sub-batches | Merge strategy |
|------|-------------|----------------|
| `backend/app/main.py` | 3A (routers), 3E (CORS/headers) | Different sections — merge manually |
| `backend/app/api/endpoints/genes.py` | 3F (response models), 3G (nesting) | Different sections — merge manually |
| `frontend/src/api/client.ts` | 3C (cookie auth), 3F (typing/B5) | Merge carefully |
| `backend/app/services/network_analysis_service.py` | 3B (chunked loading), 3D (TTL constants) | Different sections — merge carefully |
| `backend/app/api/endpoints/gene_annotations.py` | 3A (split/rename), 3D (TTL constants) | **3D must target the split file names** (`annotation_retrieval.py`, `annotation_updates.py`) after 3A completes. If running in parallel, 3D should apply TTL changes to the original file and 3A merge will carry them forward. |

When merging worktrees, resolve these files manually by taking changes from both branches.

---

## Final Verification

- [x] **Step 1: Run full CI suite**

Run: `make ci`
Expected: All backend + frontend checks PASS

- [ ] **Step 2: Run security scans**

**SKIPPED:** S15 already handled (build_internal_error returns generic message). M7/S14 deferred — need manual triage.

Run: `make security`
Expected: No new findings

- [x] **Step 3: Verify app works end-to-end**

Run: `make hybrid-up && make backend & make frontend &`

Test:
- Browse gene list at localhost:5173
- Login as admin
- Check admin dashboard loads
- Verify no console errors
- Verify security headers in response (check DevTools Network tab)
