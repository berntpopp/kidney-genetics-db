# Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close remaining gaps between the alpha state and a deployable production system — error handling, code splitting, rate limiting, CI/CD, backups, and error reporting.

**Architecture:** 8 areas across 3 implementation waves plus a pre-wave bug fix. Each wave is independently shippable. Wave 1 items are parallel with no dependencies. Waves 2 and 3 build on prior waves.

**Tech Stack:** FastAPI, SQLAlchemy, SlowAPI, Redis, Vue 3, TypeScript, Vite, GitHub Actions, Docker, postgres-backup-local

**Spec:** `.planning/specs/2026-03-10-production-readiness-design.md`

---

## File Structure

### Pre-Wave (Backup Fix)
- Modify: `backend/app/models/backup_job.py:64-73` (ENUM declarations)
- Modify: `backend/app/services/backup_service.py:559` (raw SQL)
- Create: `backend/alembic/versions/xxxx_fix_backup_enum_values.py` (migration)
- Test: `backend/tests/test_backup_service.py` (new)

### Wave 1 — Area C (Code Splitting)
- Modify: `frontend/vite.config.ts` (add manualChunks)
- Modify: `frontend/src/views/NetworkAnalysis.vue:536` (defineAsyncComponent)
- Modify: `frontend/src/views/Dashboard.vue:119-122` (defineAsyncComponent)
- Modify: `frontend/src/views/GeneStructure.vue:308-309` (defineAsyncComponent)
- Modify: `frontend/src/router/index.ts` (add router.onError)
- Create: `frontend/src/components/ui/ComponentSkeleton.vue`
- Create: `frontend/src/components/ui/ComponentError.vue`

### Wave 1 — Area E (Rate Limiting)
- Create: `backend/app/core/rate_limit.py` (limiter + key function)
- Modify: `backend/app/main.py:129-155` (register middleware + handler)
- Modify: `backend/app/api/endpoints/auth.py` (per-endpoint decorators)
- Modify: `backend/app/api/endpoints/genes.py` (per-endpoint decorators)
- Modify: `backend/app/api/endpoints/network_analysis.py` (per-endpoint decorators)
- Modify: `backend/app/api/endpoints/gene_annotations.py` (pipeline decorators)
- Modify: `backend/app/api/endpoints/statistics.py` (per-endpoint decorators)
- Modify: `backend/app/core/config.py:68` (add REDIS_RATE_LIMIT_DB)
- Modify: `backend/tests/conftest.py` (add rate limit bypass fixture)
- Create: `backend/tests/test_rate_limit.py`

### Wave 1 — Area I (Backup Sidecar)
- Modify: `docker-compose.prod.yml` (add db-backup service + volume)

### Wave 2 — Area A (Error Boundaries)
- Create: `frontend/src/components/ui/error-boundary/ErrorBoundary.vue`
- Modify: `frontend/src/main.ts` (global error handlers)
- Modify: `frontend/src/views/NetworkAnalysis.vue` (wrap NetworkGraph)
- Modify: `frontend/src/views/Dashboard.vue` (wrap charts)
- Modify: `frontend/src/views/Genes.vue` (wrap GeneTable)
- Modify: `frontend/src/views/GeneStructure.vue` (wrap visualizations)
- Modify: `frontend/src/router/index.ts` (extend router.onError from C4)

### Wave 2 — Area G (CI/CD)
- Create: `.github/workflows/cd.yml`

### Wave 2 — Area H (Deployment Docs)
- Create: `.planning/PRODUCTION-DEPLOYMENT.md`
- Modify: `docker-compose.prod.yml` (add Redis service + comments)

### Wave 3 — Area B (Error Reporting)
- Create: `backend/app/api/endpoints/client_logs.py`
- Create: `backend/app/schemas/client_log.py`
- Modify: `backend/app/main.py` (register new router)
- Modify: `frontend/src/services/logService.ts:151-158` (add _reportToBackend)
- Create: `backend/tests/test_client_logs.py`

### Wave 3 — Area F (Log Viewer Improvements)
- Modify: `frontend/src/views/admin/AdminLogViewer.vue:60-82` (add frontend filter preset)
- Modify: `backend/app/core/logging/maintenance.py:23` (read retention from settings)
- Modify: `frontend/src/views/admin/AdminSettings.vue` (add retention config UI)

---

## Chunk 1: Pre-Wave — Fix Backup Service

### Task 1: Fix backup enum case mismatch

**Files:**
- Modify: `backend/app/models/backup_job.py:64-73`
- Modify: `backend/app/services/backup_service.py:559`
- Reference: `backend/app/models/system_setting.py:43-56` (working pattern)

- [ ] **Step 1: Write a test that reproduces the 503**

File: `backend/tests/test_backup_enum.py`

```python
"""Test backup enum values match PostgreSQL expectations."""
import pytest
from app.models.backup_job import BackupStatus, BackupTrigger


@pytest.mark.unit
class TestBackupEnums:
    """Verify enum values are lowercase (matching PostgreSQL enum type)."""

    def test_backup_status_values_are_lowercase(self):
        """BackupStatus enum values must be lowercase for PostgreSQL."""
        for member in BackupStatus:
            assert member.value == member.value.lower(), (
                f"BackupStatus.{member.name} has value '{member.value}' "
                f"— must be lowercase for PostgreSQL"
            )

    def test_backup_trigger_values_are_lowercase(self):
        """BackupTrigger enum values must be lowercase for PostgreSQL."""
        for member in BackupTrigger:
            assert member.value == member.value.lower(), (
                f"BackupTrigger.{member.name} has value '{member.value}' "
                f"— must be lowercase for PostgreSQL"
            )

    def test_backup_status_column_uses_values_callable(self):
        """The SQLAlchemy ENUM column must use values_callable to send .value not .name."""
        from app.models.backup_job import BackupJob
        status_col = BackupJob.__table__.columns["status"]
        # The ENUM type should have enums matching the lowercase values
        assert "completed" in status_col.type.enums, (
            "BackupJob.status ENUM must contain lowercase 'completed' — "
            "add values_callable=lambda x: [e.value for e in x]"
        )

    def test_backup_trigger_column_uses_values_callable(self):
        """The SQLAlchemy ENUM column must use values_callable."""
        from app.models.backup_job import BackupJob
        trigger_col = BackupJob.__table__.columns["trigger_source"]
        assert "manual_api" in trigger_col.type.enums, (
            "BackupJob.trigger_source ENUM must contain lowercase 'manual_api' — "
            "add values_callable=lambda x: [e.value for e in x]"
        )
```

- [ ] **Step 2: Run test to confirm it fails**

Run: `cd backend && uv run pytest tests/test_backup_enum.py -v`
Expected: FAIL on `test_backup_status_column_uses_values_callable` (ENUM contains uppercase names)

- [ ] **Step 3: Fix the ENUM declarations in backup_job.py**

In `backend/app/models/backup_job.py`, change the status column (~line 64-68):

```python
# Before:
status = Column(
    ENUM(BackupStatus, name="backup_status", create_type=False),
    nullable=False,
    default=BackupStatus.PENDING,
    index=True,
)

# After (follow system_setting.py pattern):
# Use values_callable so SQLAlchemy sends enum .value (lowercase)
# instead of enum .name (UPPERCASE) to PostgreSQL
status = Column(
    ENUM(
        BackupStatus,
        name="backup_status",
        create_type=False,
        values_callable=lambda x: [e.value for e in x],
    ),
    nullable=False,
    default=BackupStatus.PENDING,
    index=True,
)
```

Apply same fix to trigger_source column (~line 69-73):

```python
trigger_source = Column(
    ENUM(
        BackupTrigger,
        name="backup_trigger",
        create_type=False,
        values_callable=lambda x: [e.value for e in x],
    ),
    nullable=False,
    index=True,
)
```

- [ ] **Step 4: Fix raw SQL in backup_service.py**

In `backend/app/services/backup_service.py`, find ~line 559:

```python
# Before:
"SELECT COALESCE(SUM(file_size), 0) FROM backup_jobs WHERE status = 'COMPLETED'"

# After:
"SELECT COALESCE(SUM(file_size), 0) FROM backup_jobs WHERE status = 'completed'"
```

- [ ] **Step 5: Run tests to verify fix**

Run: `cd backend && uv run pytest tests/test_backup_enum.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Generate Alembic migration for PostgreSQL enum values**

Run: `cd backend && uv run alembic revision --autogenerate -m "fix backup enum values to lowercase"`

Then edit the generated migration to include manual ALTER TYPE statements since autogenerate won't detect enum value changes:

```python
def upgrade() -> None:
    # Fix backup_status enum values from UPPERCASE to lowercase
    op.execute("ALTER TYPE backup_status RENAME VALUE 'PENDING' TO 'pending'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'RUNNING' TO 'running'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'COMPLETED' TO 'completed'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'FAILED' TO 'failed'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'RESTORED' TO 'restored'")

    # Fix backup_trigger enum values from UPPERCASE to lowercase
    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'MANUAL_API' TO 'manual_api'")
    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'SCHEDULED_CRON' TO 'scheduled_cron'")
    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'PRE_RESTORE_SAFETY' TO 'pre_restore_safety'")


def downgrade() -> None:
    op.execute("ALTER TYPE backup_status RENAME VALUE 'pending' TO 'PENDING'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'running' TO 'RUNNING'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'completed' TO 'COMPLETED'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'failed' TO 'FAILED'")
    op.execute("ALTER TYPE backup_status RENAME VALUE 'restored' TO 'RESTORED'")

    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'manual_api' TO 'MANUAL_API'")
    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'scheduled_cron' TO 'SCHEDULED_CRON'")
    op.execute("ALTER TYPE backup_trigger RENAME VALUE 'pre_restore_safety' TO 'PRE_RESTORE_SAFETY'")
```

Note: Check if enum values are already lowercase (migration may have created them correctly). If `ALTER TYPE RENAME VALUE` fails with "does not exist", the values are already correct and you can skip that line.

- [ ] **Step 7: Apply migration and verify**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration applies cleanly

- [ ] **Step 8: Verify via API**

Run:
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=ChangeMe!Admin2024" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Test stats endpoint (was returning 503)
curl -s -w "\n%{http_code}" http://localhost:8000/api/admin/backups/stats \
  -H "Authorization: Bearer $TOKEN"

# Test create endpoint (was returning 503)
curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/admin/backups/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```
Expected: 200 for stats, 200/201 for create (not 503)

- [ ] **Step 9: Run full test suite**

Run: `cd backend && uv run pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Step 10: Lint and commit**

```bash
cd backend && uv run ruff check --fix . && uv run ruff format .
git add backend/app/models/backup_job.py backend/app/services/backup_service.py \
       backend/alembic/versions/*fix_backup_enum* backend/tests/test_backup_enum.py
git commit -m "fix: resolve backup service 503 by fixing enum case mismatch"
```

---

## Chunk 2: Wave 1 — Code Splitting (Area C)

### Task 2: Add loading and error fallback components

**Files:**
- Create: `frontend/src/components/ui/ComponentSkeleton.vue`
- Create: `frontend/src/components/ui/ComponentError.vue`

- [ ] **Step 1: Create ComponentSkeleton.vue**

File: `frontend/src/components/ui/ComponentSkeleton.vue`

```vue
<script setup lang="ts">
defineProps<{
  /** Minimum height for the skeleton placeholder */
  minHeight?: string
}>()
</script>

<template>
  <div
    class="flex items-center justify-center rounded-lg border border-border bg-muted/30"
    :style="{ minHeight: minHeight ?? '200px' }"
  >
    <div class="flex flex-col items-center gap-2 text-muted-foreground">
      <svg
        class="h-6 w-6 animate-spin"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span class="text-sm">Loading component...</span>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Create ComponentError.vue**

File: `frontend/src/components/ui/ComponentError.vue`

```vue
<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** Error message to display */
  error?: Error
}>()

const emit = defineEmits<{
  retry: []
}>()

const message = computed(() => props.error?.message ?? 'Failed to load component')
</script>

<template>
  <div
    class="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-6"
    style="min-height: 200px"
  >
    <div class="flex flex-col items-center gap-3 text-center">
      <div class="rounded-full bg-destructive/10 p-3">
        <svg
          class="h-6 w-6 text-destructive"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>
      <p class="text-sm text-muted-foreground">{{ message }}</p>
      <button
        class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
        @click="emit('retry')"
      >
        Try again
      </button>
    </div>
  </div>
</template>

```

- [ ] **Step 3: Verify components render**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/ComponentSkeleton.vue \
       frontend/src/components/ui/ComponentError.vue
git commit -m "feat: add loading skeleton and error fallback components for async loading"
```

### Task 3: Wrap heavy components with defineAsyncComponent

**Files:**
- Modify: `frontend/src/views/NetworkAnalysis.vue:536`
- Modify: `frontend/src/views/Dashboard.vue:119-122`
- Modify: `frontend/src/views/GeneStructure.vue:308-309`

- [ ] **Step 1: Convert NetworkGraph to async in NetworkAnalysis.vue**

In `frontend/src/views/NetworkAnalysis.vue`, change line 536:

```typescript
// Before:
import NetworkGraph from '../components/network/NetworkGraph.vue'

// After:
import { defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'

const NetworkGraph = defineAsyncComponent({
  loader: () => import('../components/network/NetworkGraph.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})
```

Note: If `defineAsyncComponent` is already imported from vue, just add it to the existing import. Check if `ComponentSkeleton` / `ComponentError` need to be added to existing imports.

- [ ] **Step 2: Convert Dashboard charts to async in Dashboard.vue**

In `frontend/src/views/Dashboard.vue`, change lines 119-122:

```typescript
// Before:
import {
  UpSetChart,
  SourceDistributionsChart,
  EvidenceCompositionChart,
} from '@/components/visualizations'

// After:
import { defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'

const UpSetChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/UpSetChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})

const SourceDistributionsChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/SourceDistributionsChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})

const EvidenceCompositionChart = defineAsyncComponent({
  loader: () => import('@/components/visualizations/EvidenceCompositionChart.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})
```

- [ ] **Step 3: Convert GeneStructure visualizations to async**

In `frontend/src/views/GeneStructure.vue`, change lines 308-309:

```typescript
// Before:
import GeneStructureVisualization from '@/components/visualizations/GeneStructureVisualization.vue'
import ProteinDomainVisualization from '@/components/visualizations/ProteinDomainVisualization.vue'

// After:
import { defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'

const GeneStructureVisualization = defineAsyncComponent({
  loader: () => import('@/components/visualizations/GeneStructureVisualization.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})

const ProteinDomainVisualization = defineAsyncComponent({
  loader: () => import('@/components/visualizations/ProteinDomainVisualization.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000,
})
```

- [ ] **Step 4: Build and verify chunk splitting**

Run: `cd frontend && npm run build 2>&1 | grep -E '(NetworkGraph|UpSet|GeneStructure|ProteinDomain|dist/assets/)'`
Expected: These components now appear as separate chunks in the build output

- [ ] **Step 5: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/src/views/NetworkAnalysis.vue \
       frontend/src/views/Dashboard.vue \
       frontend/src/views/GeneStructure.vue
git commit -m "feat: lazy-load heavy visualization components with defineAsyncComponent"
```

### Task 4: Configure Vite manual chunks + chunk error recovery

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add manualChunks to vite.config.ts**

In `frontend/vite.config.ts`, add the build configuration:

```typescript
// Add inside defineConfig:
build: {
  rollupOptions: {
    output: {
      manualChunks: {
        'vendor-vue': ['vue', 'vue-router', 'pinia'],
        'vendor-tanstack': ['@tanstack/vue-table'],
        'vendor-d3': ['d3'],
        'vendor-cytoscape': ['cytoscape'],
      },
    },
  },
},
```

- [ ] **Step 2: Add chunk load error recovery to router**

In `frontend/src/router/index.ts`, add after the router is created (before `export default router`):

```typescript
// Handle chunk load failures (e.g., deploy during navigation)
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    window.location.href = to.fullPath
  }
})
```

- [ ] **Step 3: Build and verify vendor chunks**

Run: `cd frontend && npm run build 2>&1 | grep vendor`
Expected: Output shows `vendor-vue`, `vendor-tanstack`, `vendor-d3`, `vendor-cytoscape` chunks

- [ ] **Step 4: Verify NetworkAnalysis chunk is smaller**

Run: `cd frontend && npm run build 2>&1 | grep NetworkAnalysis`
Expected: NetworkAnalysis chunk is significantly smaller than previous 606 kB (cytoscape now in vendor-cytoscape)

- [ ] **Step 5: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/vite.config.ts frontend/src/router/index.ts
git commit -m "perf: add vendor chunk splitting and chunk load error recovery"
```

---

## Chunk 3: Wave 1 — Rate Limiting (Area E)

### Task 5: Install SlowAPI and create rate limiting module

**Files:**
- Create: `backend/app/core/rate_limit.py`
- Modify: `backend/app/core/config.py:68`

- [ ] **Step 1: Install SlowAPI**

Run: `cd backend && uv add slowapi`

- [ ] **Step 2: Add Redis rate limit DB config**

In `backend/app/core/config.py`, near the existing Redis config (~line 68):

```python
# Existing:
REDIS_URL: str = "redis://localhost:6379/0"

# Add:
REDIS_RATE_LIMIT_DB: int = 1  # Separate DB from ARQ (DB 0)
```

- [ ] **Step 3: Create rate_limit.py module**

File: `backend/app/core/rate_limit.py`

```python
"""API rate limiting using SlowAPI with Redis backend.

Provides tiered rate limiting:
- Anonymous (IP-based): 60 req/min
- Authenticated (JWT): 300 req/min
- Admin: 1000 req/min (safety net)

Uses Redis DB 1 (separate from ARQ on DB 0).
Falls back to in-memory if Redis unavailable.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_real_ip(request: Request) -> str:
    """Get real client IP, respecting X-Forwarded-For behind reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First IP in the chain is the real client
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def _get_rate_limit_key(request: Request) -> str:
    """Determine rate limit key: user ID if authenticated, else IP address."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.core.security import decode_access_token

            payload = decode_access_token(auth_header.split(" ", 1)[1])
            if payload and "sub" in payload:
                # Check for admin role — give higher limits
                role = payload.get("role", "")
                if role == "admin":
                    return f"admin:{payload['sub']}"
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return _get_real_ip(request)


def _build_redis_url() -> str:
    """Build Redis URL for rate limiting using separate DB."""
    base = settings.REDIS_URL
    # Replace DB number in URL
    if "/" in base.rsplit(":", 1)[-1]:
        # URL has a DB number, replace it
        return base.rsplit("/", 1)[0] + f"/{settings.REDIS_RATE_LIMIT_DB}"
    return f"{base}/{settings.REDIS_RATE_LIMIT_DB}"


def _get_storage_uri() -> str:
    """Get storage URI with Redis fallback to in-memory."""
    try:
        import redis

        r = redis.from_url(_build_redis_url())
        r.ping()
        uri = _build_redis_url()
        logger.sync_info("Rate limiter using Redis storage", uri=uri)
        return uri
    except Exception:
        logger.sync_warning(
            "Redis unavailable for rate limiting, using in-memory storage"
        )
        return "memory://"


limiter = Limiter(
    key_func=_get_rate_limit_key,
    storage_uri=_get_storage_uri(),
    default_limits=["60/minute"],
    headers_enabled=True,
)

# Limit strings for per-endpoint use
LIMIT_ANONYMOUS = "60/minute"
LIMIT_AUTHENTICATED = "300/minute"
LIMIT_ADMIN = "1000/minute"
LIMIT_AUTH_LOGIN = "5/minute"
LIMIT_AUTH_REGISTER = "3/minute"
LIMIT_GENE_LIST = "30/minute"
LIMIT_NETWORK = "10/minute"
LIMIT_STATISTICS = "30/minute"
LIMIT_PIPELINE = "5/hour"
LIMIT_CLIENT_LOGS = "30/minute"
```

- [ ] **Step 4: Commit**

```bash
cd backend && uv run ruff check --fix . && uv run ruff format .
git add backend/app/core/rate_limit.py backend/app/core/config.py pyproject.toml uv.lock
git commit -m "feat: add SlowAPI rate limiting module with Redis backend"
```

### Task 6: Register rate limiter middleware and add per-endpoint limits

**Files:**
- Modify: `backend/app/main.py:129-155`
- Modify: `backend/app/api/endpoints/auth.py`
- Modify: `backend/app/api/endpoints/genes.py`
- Modify: `backend/app/api/endpoints/network_analysis.py`
- Modify: `backend/app/api/endpoints/gene_annotations.py`
- Modify: `backend/app/api/endpoints/statistics.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Register middleware in main.py**

In `backend/app/main.py`, add after CORS middleware (~line 135):

```python
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.rate_limit import limiter

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
```

- [ ] **Step 2: Add per-endpoint decorators to auth.py**

In `backend/app/api/endpoints/auth.py`, add to login and register endpoints:

```python
from app.core.rate_limit import limiter, LIMIT_AUTH_LOGIN, LIMIT_AUTH_REGISTER
from slowapi.util import get_remote_address

# On the login endpoint:
@router.post("/login")
@limiter.limit(LIMIT_AUTH_LOGIN, key_func=get_remote_address)
async def login(request: Request, ...):
    ...

# On the register endpoint:
@router.post("/register")
@limiter.limit(LIMIT_AUTH_REGISTER, key_func=get_remote_address)
async def register(request: Request, ...):
    ...
```

Note: The endpoint function MUST have a `request: Request` parameter for SlowAPI to work. Add it if missing.

- [ ] **Step 3: Add per-endpoint decorators to genes.py**

```python
from app.core.rate_limit import limiter, LIMIT_GENE_LIST

# On the gene list endpoint:
@router.get("/")
@limiter.limit(LIMIT_GENE_LIST)
async def get_genes(request: Request, ...):
    ...
```

- [ ] **Step 4: Add per-endpoint decorators to network_analysis.py**

```python
from app.core.rate_limit import limiter, LIMIT_NETWORK

# On network endpoints:
@limiter.limit(LIMIT_NETWORK)
```

- [ ] **Step 5: Add per-endpoint decorators to statistics.py**

```python
from app.core.rate_limit import limiter, LIMIT_STATISTICS

@limiter.limit(LIMIT_STATISTICS)
```

- [ ] **Step 6: Add per-endpoint decorators to pipeline endpoints**

In `backend/app/api/endpoints/gene_annotations.py`, find pipeline endpoints:

```python
from app.core.rate_limit import limiter, LIMIT_PIPELINE

@limiter.limit(LIMIT_PIPELINE)
```

- [ ] **Step 7: Add rate limit bypass fixture to conftest.py**

In `backend/tests/conftest.py`, add:

```python
@pytest.fixture(autouse=True)
def disable_rate_limits():
    """Disable rate limiting during tests."""
    from app.core.rate_limit import limiter
    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original
```

- [ ] **Step 8: Write rate limit integration test**

File: `backend/tests/test_rate_limit.py`

```python
"""Test API rate limiting."""
import pytest
from unittest.mock import patch


@pytest.mark.unit
class TestRateLimitModule:
    """Test rate limit key function and configuration."""

    def test_anonymous_key_returns_ip(self):
        """Anonymous requests should be keyed by IP address."""
        from app.core.rate_limit import _get_rate_limit_key
        from unittest.mock import MagicMock

        request = MagicMock()
        request.headers = {}
        request.client.host = "1.2.3.4"
        request.scope = {"type": "http"}

        key = _get_rate_limit_key(request)
        assert "1.2.3.4" in key

    def test_limiter_is_configured(self):
        """Limiter should be configured with default limits."""
        from app.core.rate_limit import limiter

        assert limiter is not None
        assert limiter._default_limits is not None
```

- [ ] **Step 9: Run tests**

Run: `cd backend && uv run pytest tests/test_rate_limit.py -v`
Expected: PASS

- [ ] **Step 10: Run full test suite to verify no regressions**

Run: `cd backend && uv run pytest tests/ -x -q`
Expected: All tests pass (rate limiting disabled by fixture)

- [ ] **Step 11: Lint and commit**

```bash
cd backend && uv run ruff check --fix . && uv run ruff format .
git add backend/app/main.py backend/app/api/endpoints/auth.py \
       backend/app/api/endpoints/genes.py backend/app/api/endpoints/network_analysis.py \
       backend/app/api/endpoints/gene_annotations.py backend/app/api/endpoints/statistics.py \
       backend/tests/conftest.py backend/tests/test_rate_limit.py
git commit -m "feat: register SlowAPI middleware with per-endpoint rate limits"
```

---

## Chunk 4: Wave 1 — Backup Sidecar (Area I) + Wave 2 — Deployment Docs (Area H)

### Task 7: Add backup sidecar and Redis to production compose

**Files:**
- Modify: `docker-compose.prod.yml`

- [ ] **Step 1: Add Redis service to docker-compose.prod.yml**

Add after the postgres service, before the backend service:

```yaml
  redis:
    image: redis:7-alpine
    container_name: kidney_genetics_redis
    networks:
      - kidney_genetics_internal_net
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    cap_drop:
      - ALL
    cap_add:
      - SETGID
      - SETUID
```

Add `redis_data:` to the volumes section.

Add `redis` to the backend service's `depends_on`.

- [ ] **Step 2: Add backup sidecar to docker-compose.prod.yml**

Add after the frontend service:

```yaml
  db-backup:
    image: prodrigestivill/postgres-backup-local:16
    container_name: kidney_genetics_db_backup
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      SCHEDULE: "0 2 * * *"
      BACKUP_KEEP_DAYS: 7
      BACKUP_KEEP_WEEKS: 4
      BACKUP_KEEP_MONTHS: 6
      POSTGRES_EXTRA_OPTS: "--clean --if-exists --no-owner"
      HEALTHCHECK_PORT: 8081
    networks:
      - kidney_genetics_internal_net
    volumes:
      - db-backups:/backups
    restart: unless-stopped
    cap_drop:
      - ALL
```

Add `db-backups:` to the volumes section.

- [ ] **Step 3: Verify compose file syntax**

Run: `docker compose -f docker-compose.prod.yml config --quiet`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add docker-compose.prod.yml
git commit -m "feat: add Redis service and automated backup sidecar to production compose"
```

> **Deferred:** Design spec I3 (backup status warning in admin dashboard — alert if no backup in >26h) is deferred to a follow-up task. The sidecar healthcheck at `http://db-backup:8081` can be queried by the backend when this is implemented.

### Task 8: Write production deployment documentation

**Files:**
- Create: `.planning/PRODUCTION-DEPLOYMENT.md`

- [ ] **Step 1: Create production deployment doc**

File: `.planning/PRODUCTION-DEPLOYMENT.md`

```markdown
# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose v2+
- A VPS with 4+ CPU cores and 8+ GB RAM
- A domain name pointed at the server
- Nginx Proxy Manager (NPM) running on the server

## Quick Start

### 1. Create Docker Network

```bash
docker network create npm_proxy_network
```

### 2. Configure Environment

```bash
cp .env.production.example .env.production
# Edit .env.production with your values:
# - POSTGRES_PASSWORD (strong, unique)
# - SECRET_KEY (generate: openssl rand -hex 32)
# - ADMIN_USERNAME / ADMIN_PASSWORD
# - ALLOWED_ORIGINS (your domain)
```

### 3. Start Services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Configure Nginx Proxy Manager

**Frontend proxy host:**
- Domain: `your-domain.com`
- Forward hostname: `kidney_genetics_frontend`
- Forward port: `8080`
- SSL: Request Let's Encrypt certificate

**API proxy host:**
- Domain: `your-domain.com`
- Custom location: `/api` → `kidney_genetics_backend:8000`
- Custom location: `/health` → `kidney_genetics_backend:8000`
- WebSocket support: Enable for `/api/progress/ws`

**Advanced nginx config for WebSocket:**
```nginx
location /api/progress/ws {
    proxy_pass http://kidney_genetics_backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

### 5. Verify Deployment

```bash
# Health checks
curl https://your-domain.com/health        # Frontend nginx
curl https://your-domain.com/api/health    # Backend API

# Create admin user (if not auto-created)
# Done via ADMIN_USERNAME/ADMIN_PASSWORD env vars on first startup
```

### 6. Run Initial Pipeline

Via API (recommended):
```bash
curl -X POST https://your-domain.com/api/annotations/pipeline/update \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "full"}'
```

## Automated Backups

The `db-backup` sidecar automatically:
- Creates daily backups at 2:00 AM
- Keeps 7 daily, 4 weekly, 6 monthly backups
- Stores in the `db-backups` Docker volume

### Manual Backup

```bash
docker exec kidney_genetics_db_backup /backup.sh
```

### List Backups

```bash
docker exec kidney_genetics_db_backup ls -la /backups/
```

### Restore from Backup

```bash
# Stop the backend first
docker compose -f docker-compose.prod.yml stop backend

# Restore (replace filename)
docker exec -i kidney_genetics_postgres \
  pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists \
  < /path/to/backup.dump

# Restart
docker compose -f docker-compose.prod.yml up -d backend
```

## Production Checklist

- [ ] Create Docker network: `docker network create npm_proxy_network`
- [ ] Copy `.env.production.example` → `.env.production`, fill secrets
- [ ] `docker compose -f docker-compose.prod.yml up -d`
- [ ] Configure NPM proxy hosts (frontend + API)
- [ ] Request SSL certificates via NPM
- [ ] Verify health: `/health` (frontend), `/api/health` (backend)
- [ ] Create initial admin user (via env vars or API)
- [ ] Run initial data pipeline via API
- [ ] Verify WebSocket connection for pipeline progress
- [ ] Verify backup sidecar is running: `docker logs kidney_genetics_db_backup`
- [ ] Test backup restore on a non-production instance
```

- [ ] **Step 2: Commit**

```bash
git add .planning/PRODUCTION-DEPLOYMENT.md
git commit -m "docs: add production deployment guide with NPM setup and backup procedures"
```

---

## Chunk 5: Wave 2 — Error Boundaries (Area A)

### Task 9: Create ErrorBoundary component

**Files:**
- Create: `frontend/src/components/ui/error-boundary/ErrorBoundary.vue`

- [ ] **Step 1: Create ErrorBoundary.vue**

File: `frontend/src/components/ui/error-boundary/ErrorBoundary.vue`

```vue
<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Message shown when an error is caught */
    fallbackMessage?: string
    /** Optional callback when user clicks "Try again" */
    onReset?: () => void
  }>(),
  {
    fallbackMessage: 'Something went wrong while rendering this section.',
  }
)

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err: Error, instance, info) => {
  hasError.value = true
  errorMessage.value = err.message || 'Unknown error'

  // Log via logService (feeds into logStore → LogViewer + backend reporting)
  window.logService?.error('ErrorBoundary caught render error', {
    error: err.message,
    stack: err.stack,
    info,
    component: instance?.$options?.name || instance?.$options?.__name || 'unknown',
  })

  // Stop propagation — this boundary handles the error
  return false
})

function handleReset() {
  hasError.value = false
  errorMessage.value = ''
  if (props.onReset) {
    props.onReset()
  }
}
</script>

<template>
  <slot v-if="!hasError" />
  <div
    v-else
    class="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-6"
    role="alert"
  >
    <div class="flex flex-col items-center gap-3 text-center">
      <div class="rounded-full bg-destructive/10 p-3">
        <svg
          class="h-6 w-6 text-destructive"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>
      <p class="text-sm font-medium text-foreground">{{ fallbackMessage }}</p>
      <p v-if="errorMessage" class="max-w-md text-xs text-muted-foreground">
        {{ errorMessage }}
      </p>
      <button
        class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
        @click="handleReset"
      >
        <svg
          class="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
          />
        </svg>
        Try again
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Build to verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/error-boundary/ErrorBoundary.vue
git commit -m "feat: add ErrorBoundary component for catching render crashes"
```

### Task 10: Wrap high-risk components with ErrorBoundary

**Files:**
- Modify: `frontend/src/views/NetworkAnalysis.vue`
- Modify: `frontend/src/views/Dashboard.vue`
- Modify: `frontend/src/views/Genes.vue`
- Modify: `frontend/src/views/GeneStructure.vue`

- [ ] **Step 1: Wrap NetworkGraph in NetworkAnalysis.vue**

Add import and wrap the `<NetworkGraph>` usage in template:

```vue
<script setup>
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
</script>

<!-- In template, find <NetworkGraph ... /> and wrap: -->
<ErrorBoundary fallback-message="Network visualization failed to render.">
  <NetworkGraph ... />
</ErrorBoundary>
```

- [ ] **Step 2: Wrap charts in Dashboard.vue**

```vue
<script setup>
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
</script>

<!-- Wrap each chart component: -->
<ErrorBoundary fallback-message="Chart failed to render.">
  <UpSetChart ... />
</ErrorBoundary>

<ErrorBoundary fallback-message="Chart failed to render.">
  <SourceDistributionsChart ... />
</ErrorBoundary>

<ErrorBoundary fallback-message="Chart failed to render.">
  <EvidenceCompositionChart ... />
</ErrorBoundary>
```

- [ ] **Step 3: Wrap GeneTable in Genes.vue**

```vue
<script setup>
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
</script>

<ErrorBoundary fallback-message="Gene table failed to render.">
  <GeneTable ... />
</ErrorBoundary>
```

- [ ] **Step 4: Wrap visualizations in GeneStructure.vue**

```vue
<script setup>
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
</script>

<ErrorBoundary fallback-message="Gene structure visualization failed to render.">
  <GeneStructureVisualization ... />
</ErrorBoundary>

<ErrorBoundary fallback-message="Protein domain visualization failed to render.">
  <ProteinDomainVisualization ... />
</ErrorBoundary>
```

- [ ] **Step 5: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 6: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/src/views/NetworkAnalysis.vue frontend/src/views/Dashboard.vue \
       frontend/src/views/Genes.vue frontend/src/views/GeneStructure.vue
git commit -m "feat: wrap high-risk components with ErrorBoundary"
```

### Task 11: Add global error handlers to main.ts and extend router.onError

**Files:**
- Modify: `frontend/src/main.ts`
- Modify: `frontend/src/router/index.ts`

- [ ] **Step 1: Add global error handlers to main.ts**

In `frontend/src/main.ts`, add after `app.use(router)` (~line 48):

```typescript
// Global Vue error handler — catches unhandled errors in components
app.config.errorHandler = (err, instance, info) => {
  const logService = window.logService
  if (logService) {
    logService.error('Unhandled Vue error', {
      error: err instanceof Error ? err.message : String(err),
      stack: err instanceof Error ? err.stack : undefined,
      info,
      component: (instance as any)?.$options?.name || 'unknown',
    })
  } else {
    console.error('Unhandled Vue error:', err, info)
  }
}

// Catch unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
  const logService = window.logService
  if (logService) {
    logService.error('Unhandled promise rejection', {
      reason:
        event.reason instanceof Error
          ? { message: event.reason.message, stack: event.reason.stack }
          : String(event.reason),
    })
  }
})
```

- [ ] **Step 2: Extend router.onError from C4**

In `frontend/src/router/index.ts`, update the `router.onError` handler added in Task 4 (C4):

```typescript
// Replace the C4 handler with the extended version:
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    // Chunk load failure — full page reload to get new chunks
    window.location.href = to.fullPath
  } else {
    // Log other navigation errors
    window.logService?.error('Navigation error', {
      error: error.message,
      stack: error.stack,
      route: to.fullPath,
    })
  }
})
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/src/main.ts frontend/src/router/index.ts
git commit -m "feat: add global Vue error handler and unhandled rejection listener"
```

---

## Chunk 6: Wave 2 — CI/CD Pipeline (Area G)

### Task 12: Create CD workflow for Docker build + GHCR push

**Files:**
- Create: `.github/workflows/cd.yml`

- [ ] **Step 1: Create cd.yml**

File: `.github/workflows/cd.yml`

```yaml
name: CD — Build & Publish Docker Images

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      tag:
        description: 'Image tag override (default: git tag or sha)'
        required: false

permissions:
  contents: read
  packages: write
  security-events: write

concurrency:
  group: cd-${{ github.ref }}
  cancel-in-progress: false

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ghcr.io/${{ github.repository }}/backend
  FRONTEND_IMAGE: ghcr.io/${{ github.repository }}/frontend

jobs:
  lint-dockerfiles:
    name: Lint Dockerfiles
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Lint backend Dockerfile
        uses: hadolint/hadolint-action@v3.1.0
        with:
          dockerfile: backend/Dockerfile

      - name: Lint frontend Dockerfile
        uses: hadolint/hadolint-action@v3.1.0
        with:
          dockerfile: frontend/Dockerfile

  build-backend:
    name: Build & Push Backend
    runs-on: ubuntu-latest
    needs: lint-dockerfiles
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.BACKEND_IMAGE }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,prefix=

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-frontend:
    name: Build & Push Frontend
    runs-on: ubuntu-latest
    needs: lint-dockerfiles
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.FRONTEND_IMAGE }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,prefix=

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: ./frontend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: [build-backend, build-frontend]
    strategy:
      matrix:
        image:
          - name: backend
            path: backend
          - name: frontend
            path: frontend
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Get image tag
        id: tag
        run: |
          if [[ "${{ github.ref_type }}" == "tag" ]]; then
            echo "tag=${GITHUB_REF#refs/tags/v}" >> "$GITHUB_OUTPUT"
          else
            echo "tag=$(git rev-parse --short HEAD)" >> "$GITHUB_OUTPUT"
          fi

      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@0.28.0
        with:
          image-ref: 'ghcr.io/${{ github.repository }}/${{ matrix.image.name }}:${{ steps.tag.outputs.tag }}'
          format: sarif
          output: trivy-${{ matrix.image.name }}.sarif
          severity: CRITICAL,HIGH

      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: trivy-${{ matrix.image.name }}.sarif
          category: trivy-${{ matrix.image.name }}

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: scan
    if: github.ref_type == 'tag'
    environment: production
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd ${{ secrets.DEPLOY_PATH }}
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml up -d
            docker image prune -f
```

- [ ] **Step 2: Verify workflow YAML syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/cd.yml'))" && echo "Valid YAML"`
Expected: "Valid YAML"

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/cd.yml
git commit -m "feat: add CD workflow for Docker build, GHCR push, security scan, and deploy"
```

---

## Chunk 7: Wave 3 — Frontend Error Reporting (Area B)

### Task 13: Create backend client-logs endpoint

**Files:**
- Create: `backend/app/schemas/client_log.py`
- Create: `backend/app/api/endpoints/client_logs.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/test_client_logs.py`

- [ ] **Step 1: Write the test**

File: `backend/tests/test_client_logs.py`

```python
"""Test client-side log reporting endpoint."""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
class TestClientLogsEndpoint:
    """Test POST /api/client-logs."""

    def test_accepts_valid_error_log(self, client: TestClient):
        """Valid error log should be accepted."""
        response = client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
                "message": "Unhandled Vue error",
                "error_type": "TypeError",
                "error_message": "Cannot read properties of null",
                "url": "https://example.com/genes/HNF1B",
                "user_agent": "Mozilla/5.0",
            },
        )
        assert response.status_code == 201

    def test_rejects_invalid_level(self, client: TestClient):
        """Invalid log level should be rejected."""
        response = client.post(
            "/api/client-logs",
            json={
                "level": "INVALID",
                "message": "test",
            },
        )
        assert response.status_code == 422

    def test_requires_message(self, client: TestClient):
        """Message field is required."""
        response = client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
            },
        )
        assert response.status_code == 422

    def test_no_auth_required(self, client: TestClient):
        """Endpoint should be public (no auth required)."""
        response = client.post(
            "/api/client-logs",
            json={
                "level": "ERROR",
                "message": "test error",
            },
        )
        # Should not be 401 or 403
        assert response.status_code in (201, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_client_logs.py -v`
Expected: FAIL (endpoint doesn't exist yet)

- [ ] **Step 3: Create Pydantic schema**

File: `backend/app/schemas/client_log.py`

```python
"""Schemas for client-side log reporting."""
from typing import Optional

from pydantic import BaseModel, Field


class ClientLogCreate(BaseModel):
    """Schema for incoming client-side log entries."""

    level: str = Field(
        ...,
        pattern="^(DEBUG|INFO|WARN|ERROR|CRITICAL)$",
        description="Log level",
    )
    message: str = Field(..., max_length=2000, description="Log message")
    error_type: Optional[str] = Field(
        None, max_length=200, description="Error class name"
    )
    error_message: Optional[str] = Field(
        None, max_length=2000, description="Error message"
    )
    stack_trace: Optional[str] = Field(
        None, max_length=10000, description="Error stack trace"
    )
    url: Optional[str] = Field(
        None, max_length=2000, description="Page URL where error occurred"
    )
    user_agent: Optional[str] = Field(
        None, max_length=500, description="Browser user agent"
    )
    context: Optional[dict] = Field(
        None, description="Additional context (JSONB)"
    )


class ClientLogResponse(BaseModel):
    """Response after accepting a client log."""

    status: str = "accepted"
```

- [ ] **Step 4: Create endpoint**

File: `backend/app/api/endpoints/client_logs.py`

```python
"""Client-side log reporting endpoint.

Accepts ERROR/CRITICAL logs from the frontend logService and
writes them to the system_logs table with logger='frontend'.
Public endpoint (no auth required), rate-limited to 30/min per IP.
"""

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.logging import get_logger
from app.core.rate_limit import limiter, LIMIT_CLIENT_LOGS
from app.db.session import get_db
from app.models.system_logs import SystemLog
from app.schemas.client_log import ClientLogCreate, ClientLogResponse

from fastapi import Depends

logger = get_logger(__name__)

router = APIRouter(prefix="/client-logs", tags=["client-logs"])


@router.post("", response_model=ClientLogResponse, status_code=201)
@limiter.limit(LIMIT_CLIENT_LOGS)
async def report_client_log(
    request: Request,
    log_entry: ClientLogCreate,
    db: Session = Depends(get_db),
):
    """Accept a client-side log entry and store in system_logs."""
    client_ip = request.client.host if request.client else "unknown"

    # Write to system_logs table
    system_log = SystemLog(
        level=log_entry.level,
        logger="frontend",
        message=log_entry.message,
        context={
            "error_type": log_entry.error_type,
            "error_message": log_entry.error_message,
            "frontend_url": log_entry.url,
            "frontend_context": log_entry.context,
        },
        ip_address=client_ip,
        user_agent=log_entry.user_agent,
        error_type=log_entry.error_type,
        error_message=log_entry.error_message,
        stack_trace=log_entry.stack_trace,
    )

    await run_in_threadpool(lambda: _save_log(db, system_log))
    await logger.info(
        "Client log received",
        level=log_entry.level,
        ip=client_ip,
    )

    return ClientLogResponse()


def _save_log(db: Session, log: SystemLog) -> None:
    """Save log entry to database (sync, runs in thread pool)."""
    db.add(log)
    db.commit()
```

- [ ] **Step 5: Register router in main.py**

In `backend/app/main.py`, add with the other router includes:

```python
from app.api.endpoints.client_logs import router as client_logs_router
app.include_router(client_logs_router, prefix="/api")
```

- [ ] **Step 6: Run tests**

Run: `cd backend && uv run pytest tests/test_client_logs.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Run full test suite**

Run: `cd backend && uv run pytest tests/ -x -q`
Expected: All pass

- [ ] **Step 8: Lint and commit**

```bash
cd backend && uv run ruff check --fix . && uv run ruff format .
git add backend/app/schemas/client_log.py backend/app/api/endpoints/client_logs.py \
       backend/app/main.py backend/tests/test_client_logs.py
git commit -m "feat: add POST /api/client-logs endpoint for frontend error reporting"
```

### Task 14: Add backend reporting to logService

**Files:**
- Modify: `frontend/src/services/logService.ts:151-158`

- [ ] **Step 1: Add _reportToBackend method and queue to logService**

In `frontend/src/services/logService.ts`, add these properties and methods to the LogService class:

```typescript
// Add to class properties:
private _reportQueue: Array<Record<string, unknown>> = []
private _reportTimer: ReturnType<typeof setTimeout> | null = null
private _reportInterval = 5000 // 5 seconds between batches
private _maxQueueSize = 10

// Add this method:
private _reportToBackend(entry: LogEntry): void {
  // Only report ERROR and CRITICAL to backend
  if (entry.level !== 'ERROR' && entry.level !== 'CRITICAL') return

  this._reportQueue.push({
    level: entry.level,
    message: entry.message,
    error_type: typeof entry.data === 'object' && entry.data !== null
      ? (entry.data as Record<string, unknown>).error_type ?? (entry.data as Record<string, unknown>).error ?? undefined
      : undefined,
    error_message: typeof entry.data === 'object' && entry.data !== null
      ? (entry.data as Record<string, unknown>).error_message ?? (entry.data as Record<string, unknown>).error ?? undefined
      : undefined,
    stack_trace: typeof entry.data === 'object' && entry.data !== null
      ? (entry.data as Record<string, unknown>).stack ?? undefined
      : undefined,
    url: entry.url || window.location.href,
    user_agent: entry.userAgent || navigator.userAgent,
    context: entry.data,
  })

  // Trim queue if too large
  if (this._reportQueue.length > this._maxQueueSize) {
    this._reportQueue = this._reportQueue.slice(-this._maxQueueSize)
  }

  // Debounce: send batch after interval
  if (!this._reportTimer) {
    this._reportTimer = setTimeout(() => {
      this._flushReportQueue()
      this._reportTimer = null
    }, this._reportInterval)
  }
}

private _flushReportQueue(): void {
  if (this._reportQueue.length === 0) return

  const batch = [...this._reportQueue]
  this._reportQueue = []

  // Send each entry (sendBeacon for reliability)
  for (const entry of batch) {
    try {
      const blob = new Blob([JSON.stringify(entry)], { type: 'application/json' })
      const apiUrl = (window as any).__app_config?.apiBaseUrl ?? ''
      navigator.sendBeacon(`${apiUrl}/api/client-logs`, blob)
    } catch {
      // Silently fail — backend reporting is best-effort
    }
  }
}
```

Then in the `_log` method, after the logStore addition (~line 158), add:

```typescript
// Report ERROR/CRITICAL to backend
this._reportToBackend(entry)
```

Also add a flush on page unload in the constructor or init method:

```typescript
// Flush pending reports on page unload
window.addEventListener('beforeunload', () => {
  this._flushReportQueue()
})
```

- [ ] **Step 2: Update the apiBaseUrl reference**

The `_flushReportQueue` method needs the API base URL. Check how `config.ts` exports it and import accordingly:

```typescript
import { config } from '@/config'

// Then in _flushReportQueue, use:
const apiUrl = config.apiBaseUrl
```

- [ ] **Step 3: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 4: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/src/services/logService.ts
git commit -m "feat: add backend error reporting to logService for ERROR/CRITICAL levels"
```

---

## Chunk 8: Wave 3 — Admin Log Viewer Improvements (Area F)

### Task 15: Add frontend log source filter to AdminLogViewer

**Files:**
- Modify: `frontend/src/views/admin/AdminLogViewer.vue:60-82`

- [ ] **Step 1: Add frontend filter preset button**

In `frontend/src/views/admin/AdminLogViewer.vue`, add a quick-filter button near the existing filter controls. Find the filter section and add:

```vue
<!-- Add near the existing Source Module filter -->
<button
  class="inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm"
  :class="filters.source === 'frontend'
    ? 'border-primary bg-primary/10 text-primary'
    : 'border-border text-muted-foreground hover:bg-muted'"
  @click="toggleFrontendFilter"
>
  <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a9 9 0 01-9 9m9-15a9 9 0 00-9-9" />
  </svg>
  Frontend Errors
</button>
```

Add the toggle method:

```typescript
function toggleFrontendFilter() {
  if (filters.value.source === 'frontend') {
    filters.value.source = ''
  } else {
    filters.value.source = 'frontend'
  }
  fetchLogs()
}
```

- [ ] **Step 2: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Lint and commit**

```bash
cd frontend && npm run lint -- --fix
git add frontend/src/views/admin/AdminLogViewer.vue
git commit -m "feat: add frontend error log quick-filter to admin log viewer"
```

### Task 16: Make log retention configurable via admin settings

**Files:**
- Modify: `backend/app/core/logging/maintenance.py:23`
- Modify: `frontend/src/views/admin/AdminSettings.vue`

- [ ] **Step 1: Update LogMaintenance to read retention from settings**

In `backend/app/core/logging/maintenance.py`, modify the constructor (~line 21-37) to accept a dynamic retention_days source:

```python
# In the cleanup_old_logs method, before using self.retention_days:
# Try to read from settings table first
try:
    from app.models.system_setting import SystemSetting
    setting = db.query(SystemSetting).filter_by(
        key="log_retention_days"
    ).first()
    if setting:
        retention_days = int(setting.value)
    else:
        retention_days = self.retention_days
except Exception:
    retention_days = self.retention_days
```

Note: The `db` session must be available in the cleanup method. Check how it's currently called and ensure the session is passed through.

- [ ] **Step 2: Add log retention setting to admin settings UI**

In `frontend/src/views/admin/AdminSettings.vue`, add a log retention field in the appropriate settings section:

```vue
<!-- Add in the system settings section -->
<div class="space-y-2">
  <label class="text-sm font-medium">Log Retention (days)</label>
  <input
    v-model.number="settings.log_retention_days"
    type="number"
    min="1"
    max="365"
    class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
  />
  <p class="text-xs text-muted-foreground">
    Logs older than this will be automatically cleaned up. Default: 30 days.
  </p>
</div>
```

Note: Check how AdminSettings.vue currently loads/saves settings and follow the same pattern for this new field.

- [ ] **Step 3: Build and verify**

Run:
```bash
cd frontend && npm run build
cd ../backend && uv run ruff check --fix . && uv run ruff format .
```
Expected: Both succeed

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/logging/maintenance.py \
       frontend/src/views/admin/AdminSettings.vue
git commit -m "feat: make log retention days configurable via admin settings"
```

---

## Final Verification

- [ ] **Run full backend test suite**

Run: `cd backend && uv run pytest tests/ -x -q`
Expected: All tests pass

- [ ] **Run frontend build**

Run: `cd frontend && npm run build`
Expected: Build succeeds, vendor chunks visible, no warnings about chunk size (except possibly NetworkAnalysis if cytoscape is still large)

- [ ] **Run frontend lint**

Run: `cd frontend && npm run lint`
Expected: No errors

- [ ] **Run backend lint**

Run: `cd backend && uv run ruff check . && uv run ruff format --check .`
Expected: No errors

- [ ] **Verify backup endpoint works**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=ChangeMe!Admin2024" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8000/api/admin/backups/stats -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
Expected: 200 with valid JSON stats

- [ ] **Verify rate limiting works**

```bash
# Should get rate limited after 5 rapid login attempts
for i in $(seq 1 7); do
  echo "Attempt $i:"
  curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=wrong&password=wrong"
  echo
done
```
Expected: First 5 return 401, last 2 return 429

- [ ] **Verify client-logs endpoint works**

```bash
curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/client-logs \
  -H "Content-Type: application/json" \
  -d '{"level":"ERROR","message":"test frontend error"}'
```
Expected: 201
