# Production Readiness — Design Specification

**Date:** 2026-03-10
**Status:** Approved
**Goal:** Close remaining gaps between the alpha state and a deployable production system.

---

## Scope

8 areas across 3 waves, plus 1 pre-wave bug fix. Covers frontend resilience, backend API protection, CI/CD automation, and operational infrastructure.

### Dropped from Original Plan
- **D (Web Vitals)** — YAGNI for current user base and single-VPS deployment
- **H2 (env-config.js)** — already implemented (`docker-entrypoint.sh` + `config.ts`)
- **F2/F3 (uptime widget, error sparkline)** — nice-to-haves, not needed for production readiness

---

## Pre-Wave: Fix Backup Service (Bug)

### Problem
`/api/admin/backups/stats` and `/api/admin/backups/create` return 503. Root cause: PostgreSQL enum case mismatch.

### Root Cause
`BackupStatus` is `(str, enum.Enum)` with `COMPLETED = "completed"` — the `.value` is lowercase. However, `ENUM(BackupStatus, name="backup_status", create_type=False)` without `values_callable` uses the enum **name** (`COMPLETED`) rather than the enum **value** (`"completed"`) when communicating with PostgreSQL. Same issue for `BackupTrigger`. This exact pattern was already solved in `system_setting.py` (lines 43-52).

1. **`backup_job.py`**: Both ENUM columns lack `values_callable`, causing name/value mismatch.
2. **`backup_service.py` ~line 559**: Raw SQL uses `'COMPLETED'` (uppercase name) instead of `'completed'` (lowercase value).

### Fix
1. Add `values_callable=lambda e: [x.value for x in e]` to both ENUM column declarations in `backup_job.py` (follow `system_setting.py` pattern).
2. Fix the raw SQL string in `backup_service.py` to use lowercase `'completed'`.
3. Generate an Alembic migration to fix the existing PostgreSQL enum type values. Since the ENUM columns use `create_type=False`, the types were created by a prior migration with uppercase values. Use `ALTER TYPE backup_status RENAME VALUE 'COMPLETED' TO 'completed'` (PostgreSQL 10+) for each value in both enum types.
4. Verify via admin UI: create backup, list backups, check stats.

---

## Wave 1 (Parallel — No Dependencies)

### C: Route-Level Code Splitting + Lazy Loading

**Current state:** All routes already use lazy `() => import(...)` syntax in `router/index.ts` — C1 is done. Vite splits per-route automatically. Main entry chunk is 492 kB (158 kB gzip). NetworkAnalysis chunk is 606 kB (186 kB gzip) — triggers Vite's warning. Vendor libs (D3, Cytoscape, TanStack) are mixed with app code, causing poor cache invalidation.

#### ~~C1. Lazy route imports~~ (Already Done)

All routes in `frontend/src/router/index.ts` already use dynamic imports (`component: () => import('../views/Home.vue')`). No changes needed.

#### C2. `defineAsyncComponent` for heavy sub-components

Wrap with loading skeleton and error fallback:
- `NetworkGraph` (~606 kB chunk, only on network page)
- `UpSetChart` (only on dashboard, D3-heavy)
- `GeneStructureVisualization` (only on gene detail structure tab)
- `ProteinDomainVisualization` (only on gene detail structure tab)
- `ClusterDetailsDialog` (only on network page, on click)

Each gets:
- Loading: skeleton placeholder matching component dimensions
- Error: styled card with error message + "Try again" button (reuse pattern from Area A's ErrorBoundary)
- Timeout: 10 seconds before showing error state

Example:
```typescript
import { defineAsyncComponent } from 'vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'

const NetworkGraph = defineAsyncComponent({
  loader: () => import('@/components/network/NetworkGraph.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,       // ms before showing loading
  timeout: 10000,   // ms before showing error
})
```

#### C3. Vite manual chunks

File: `frontend/vite.config.ts`

```typescript
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
}
```

Separates rarely-changing vendor code for better cache hit rates.

#### C4. Chunk load error recovery

Initial handler for chunk load failures. Area A4 (Wave 2) will extend this handler to also log non-chunk navigation errors.

```typescript
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    window.location.href = to.fullPath
  }
})
```

#### Verification
- `npm run build` succeeds, no new warnings
- Network tab shows chunks loading on-demand
- Bundle analyzer confirms vendor chunks separated
- Navigate to admin → admin chunk loads only then
- Simulate chunk load failure → page reloads, not blank

---

### E: Backend API Rate Limiting (Layered)

**Architecture:** Nginx outer shield (coarse DDoS protection) + SlowAPI inner limits (smart per-user/per-endpoint control).

**VPS context:** 4 CPU, 8 GB RAM. Realistic mixed throughput ~300-500 req/s.

#### E1. Install SlowAPI

```bash
cd backend && uv add slowapi
```

#### E2. Rate limiting module

File: `backend/app/core/rate_limit.py`

Key function determines rate limit identity:
- Authenticated user (JWT) → `user:{user_id}` — higher limits
- Anonymous → `ip:{remote_addr}` — default limits
- Admin role → exempt or 1000/min safety net

Storage: Redis DB 1 (ARQ uses DB 0), configured via `KG_REDIS_RATE_LIMIT_DB` environment variable. Fallback: in-memory if Redis unavailable.

**Note:** `docker-compose.prod.yml` currently has no Redis service. A Redis service must be added to the production compose file for both ARQ worker and rate limiting. Follow the Redis configuration pattern from `docker-compose.services.yml`.

#### E3. Register in `main.py`

- Add `SlowAPIMiddleware`
- Add `RateLimitExceeded` exception handler → 429 JSON response with `Retry-After` header
- Enable `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` response headers

#### E4. Rate limit tiers

**Global defaults:**

| Tier | Limit | Rationale |
|------|-------|-----------|
| Anonymous (IP) | 60/min | Conservative for 4-CPU VPS, never hit by normal browsing |
| Authenticated (JWT) | 300/min | 5x anonymous, rewards having an account |
| Admin | No limit (1000/min safety) | Admins run pipeline ops, shouldn't be throttled |

**Per-endpoint overrides:**

| Endpoint | Anonymous | Authenticated | Rationale |
|----------|-----------|--------------|-----------|
| `GET /api/genes` | 30/min | 120/min | Heavier paginated query |
| `GET /api/genes/{id}` | 60/min | 300/min | Light, use global |
| `GET /api/network/*` | 10/min | 30/min | Compute-heavy |
| `GET /api/statistics/*` | 30/min | 120/min | Materialized view reads |
| `POST /api/auth/login` | 5/min (IP-forced) | N/A | Brute-force protection |
| `POST /api/auth/register` | 3/min (IP-forced) | N/A | Abuse prevention |
| `POST /api/pipeline/*` | Blocked (auth required) | 5/hour (admin) | Long-running, ~582s each |
| `POST /api/client-logs` | 30/min | 30/min | Frontend error reporting |

**Industry comparison:** NCBI uses 3/s (180/min) without key, 10/s (600/min) with key. Ensembl uses 15/s (~900/min). Our limits are more conservative, appropriate for a 4-CPU VPS vs their large infrastructure.

#### E5. Nginx outer shield (optional hardening)

Add to production nginx config if DDoS becomes a concern. Can be deferred since SlowAPI handles application-level rate limiting:
- `limit_req_zone` with 100 req/s hard cap per IP
- Connection limit of 50 concurrent per IP
- These catch floods before they reach FastAPI

#### E6. Test bypass

```python
# conftest.py
@pytest.fixture(autouse=True)
def disable_rate_limits(app):
    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True
```

#### Verification
- Exceed login limit → 429 with Retry-After header
- Normal browsing → no rate limit hits
- `make test` passes (tests bypass rate limiting)
- Response headers show `X-RateLimit-*` values

---

### I: Automated Database Backups

**Architecture:** Sidecar container for scheduled backups + existing BackupService for on-demand.

#### I1. Backup sidecar in `docker-compose.prod.yml`

```yaml
db-backup:
  image: prodrigestivill/postgres-backup-local:16
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
  volumes:
    - db-backups:/backups
  restart: unless-stopped
  cap_drop:
    - ALL
```

#### I2. Add `db-backups` named volume

Add to the volumes section of `docker-compose.prod.yml`.

#### I3. Admin dashboard backup status

Add a warning indicator to AdminDashboard if no sidecar backup exists in >26 hours. The backend can query the sidecar's healthcheck at `http://db-backup:8081` (same internal Docker network) or mount the `db-backups` volume read-only to check file timestamps.

#### I4. Document restore procedure

In `.planning/` or inline comments: how to list, restore, verify, and handle emergency recovery.

#### Verification
- Sidecar starts and creates first backup at scheduled time
- Old backups rotated per retention policy
- Restore works on test instance

---

## Wave 2 (Builds on Wave 1)

### A: Error Boundaries + Global Error Handling

**Strategy:** Error boundaries for catastrophic render crashes. Toast notifications for API failures. Both log via logService.

#### A1. `ErrorBoundary.vue` component

File: `frontend/src/components/ui/error-boundary/ErrorBoundary.vue`

- Uses `onErrorCaptured` to catch child render/lifecycle errors
- Props: `fallbackMessage` (string), optional `onReset` callback
- Shows error message + "Try again" button using existing Card + Alert components
- Calls `logService.error()` on capture (feeds into logStore → client LogViewer, and via Area B → backend)
- Returns `false` from `onErrorCaptured` to stop propagation

#### A2. Wrap high-risk components

Add `<ErrorBoundary>` around:
- `NetworkGraph` in `NetworkAnalysis.vue`
- D3 chart components in `Dashboard.vue` (UpSetChart, etc.)
- `GeneTable` in `Genes.vue`
- `GeneStructureVisualization` and `ProteinDomainVisualization` in `GeneDetail.vue`
- Each admin view's main content area

These pair naturally with C2's `defineAsyncComponent` wrappers — the error boundary catches both async load failures and runtime render errors.

#### A3. Global error handlers in `main.ts`

```typescript
app.config.errorHandler = (err, instance, info) => {
  logService.error('Unhandled Vue error', { error: err, info })
}

window.addEventListener('unhandledrejection', (event) => {
  logService.error('Unhandled promise rejection', { reason: event.reason })
})
```

#### A4. Extend route-level error handling (from C4)

Modify the `router.onError` handler added in C4 to also log non-chunk navigation errors:

```typescript
// Extends the C4 handler — do NOT add a second router.onError, modify the existing one
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    window.location.href = to.fullPath  // From C4
  } else {
    logService.error('Navigation error', { error, route: to.fullPath })
  }
})
```

#### Error flow summary

```
Render crash  → ErrorBoundary → fallback UI + logService.error()
API failure   → catch block   → toast.error() + logService.error()
Uncaught sync → errorHandler  → logService.error()
Uncaught async→ unhandledrej. → logService.error()
All paths     → logStore      → LogViewer (Ctrl+Shift+L)
                              → POST /api/client-logs (Area B)
```

#### Verification
- Throw in a wrapped component → error boundary catches, page stays functional
- Unhandled promise rejection → appears in LogViewer
- `npm run build` passes
- No console errors during normal operation

---

### G: CI/CD Docker Build + Push to GHCR

**Trigger:** Push to `v*` tags + manual `workflow_dispatch`.

#### G1. Create `.github/workflows/cd.yml`

**Jobs:**

1. **lint-dockerfiles** — Hadolint on both `backend/Dockerfile` and `frontend/Dockerfile`
2. **build-backend** — Build + push `ghcr.io/<repo>/backend`
3. **build-frontend** — Build + push `ghcr.io/<repo>/frontend`
4. **scan** — Trivy + Dockle on built images, SARIF upload to GitHub Security tab
5. **deploy** (optional) — requires `production` GitHub Environment with reviewers

**Tagging strategy:**
- `v1.2.3` → tags: `1.2.3`, `1.2`, `1`, `latest`
- Commit SHA short tag for traceability
- Use `docker/metadata-action@v5` for automatic tag generation

**Caching:**
- `cache-from: type=gha` + `cache-to: type=gha,mode=max`

**Permissions:**
- `contents: read`, `packages: write`, `security-events: write`

#### G2. GitHub Environment protection

- Create `production` environment with required reviewers
- Deploy job requires approval before running

#### G3. Deploy step

SSH-based deploy (matches phentrieve pattern):
- `appleboy/ssh-action@v1` to SSH into server
- Pull new images, `docker compose -f docker-compose.prod.yml up -d`, prune old images

#### Verification
- Push `v*` tag → images appear in GHCR
- Trivy results in GitHub Security tab
- Deploy updates running containers on server

---

### H: Production Deployment Documentation

**No code changes** — runtime config already implemented.

#### H1. Document Nginx Proxy Manager setup

Add comments to `docker-compose.prod.yml` and create `.planning/PRODUCTION-DEPLOYMENT.md`:
- NPM network creation: `docker network create npm_proxy_network`
- Proxy host config for frontend (8080) and backend API (8000)
- SSL via Let's Encrypt (NPM handles this)
- WebSocket support for `/api/progress/ws`
- Custom locations: `/api` → backend:8000, `/` → frontend:8080

#### H2. Production checklist

```
- [ ] Create Docker network: docker network create npm_proxy_network
- [ ] Copy .env.production.example → .env.production, fill secrets
- [ ] docker compose -f docker-compose.prod.yml up -d
- [ ] Configure NPM proxy hosts (frontend + API)
- [ ] Request SSL certificates via NPM
- [ ] Verify health: /health (frontend), /api/health (backend)
- [ ] Create initial admin user
- [ ] Run initial data pipeline via API
- [ ] Verify WebSocket connection for pipeline progress
- [ ] Verify automated backup sidecar is running
```

---

## Wave 3 (Builds on Wave 2)

### B: Frontend Error Reporting to Backend

**Architecture:** logService ships ERROR/CRITICAL entries to backend via `POST /api/client-logs`. Uses `navigator.sendBeacon()` for reliability.

#### B1. Backend endpoint

File: `backend/app/api/endpoints/client_logs.py`

- `POST /api/client-logs` — public (no auth required)
- Accepts: `level`, `message`, `error_type`, `error_message`, `stack_trace`, `url`, `user_agent`, `context` (JSONB)
- Rate-limited: 30/min per IP (from Area E)
- Writes to `system_logs` table with `logger='frontend'`
- Endpoint's own operational logging uses `get_logger(__name__)` from `app.core.logging` (per CLAUDE.md conventions)
- Pydantic schema for validation

#### B2. logService backend reporting

File: `frontend/src/services/logService.ts`

Add `_reportToBackend()` method inside logService:
- Triggers for ERROR and CRITICAL levels only
- Uses `navigator.sendBeacon()` for reliability (fires even on page unload)
- Batches: max 1 request per 5 seconds, queue up to 10 entries
- Includes: URL, user agent, app version, error stack trace
- Respects existing sanitization (logSanitizer already strips auth tokens, PII, genetic data)
- Graceful degradation: silently fails if backend unreachable

#### B3. Frontend log source in admin

- AdminLogViewer already filters by source module — add preset filter button for `logger='frontend'`

#### Verification
- Trigger frontend error → appears in AdminLogViewer within 10 seconds
- `sendBeacon` fires on page close with queued errors
- No PII in reported errors (sanitizer handles this)
- Rate limit not hit during normal error rates

---

### F: Admin Log Viewer Improvements (Partial)

#### F1. Frontend error log filter

Add to `AdminLogViewer.vue`:
- Quick-filter button/tab for `logger='frontend'` logs
- Show URL and user agent prominently in log detail modal
- Group by error type for deduplication view

#### F4. Configurable log retention

- Add log retention days setting to admin Settings page
- Currently hardcoded in `LogMaintenance` — read from `settings` table instead
- Admin can adjust from UI without redeployment
- Default: current value (whatever LogMaintenance uses today)

#### Verification
- Frontend errors appear with source filter in admin viewer
- Changing retention setting takes effect on next cleanup cycle

---

## Implementation Wave Summary

```
Pre-Wave (bug fix):
  └── Fix backup enum case mismatch (backup_job.py + backup_service.py)

Wave 1 (parallel):
  ├── C: Code splitting (frontend only)
  ├── E: Rate limiting (backend + nginx config)
  └── I: Backup sidecar (docker-compose only)

Wave 2 (parallel within wave):
  ├── A: Error boundaries (frontend, pairs with C)
  ├── G: CI/CD workflow (GitHub Actions)
  └── H: Documentation (no code)

Wave 3 (parallel within wave):
  ├── B: Error reporting (backend endpoint + logService extension)
  └── F1+F4: Log viewer filter + retention config
```

## Out of Scope

| Item | Reason |
|------|--------|
| MFA | Overkill for current user base |
| External alerting (Grafana, PagerDuty) | Admin dashboard sufficient |
| Log aggregation (ELK, Loki) | DB-backed log viewer adequate |
| Database HA / replication | Single instance sufficient |
| CDN | Static assets small, NPM handles SSL |
| Feature flags | Redeployment is fast |
| GlitchTip/Sentry | Start with logService → backend; add later if needed |
| Web Vitals (Area D) | YAGNI — revisit when performance complaints arise |
