# Production Readiness Plan

**Goal:** Close the remaining gaps between the current alpha state and a deployable production system. Covers code quality fixes from verified review, frontend resilience and performance, backend API protection, CI/CD automation, and operational infrastructure.

**Reference implementation:** `../phentrieve/` (same author, already deployed via GHCR + Nginx Proxy Manager)
**Review reference:** `CODEBASE_REVIEW_REPORT.md` (verified 2026-03-10, 28 confirmed issues)

---

## Scope Summary

| Area | What | Priority |
|------|------|----------|
| **P0** | **Code quality fixes from verified review** | **CRITICAL** |
| A | Frontend error boundaries + global error handling | HIGH |
| B | Frontend error reporting (GlitchTip / Sentry SDK) | MEDIUM |
| C | Route-level code splitting + lazy loading | HIGH |
| D | Web Vitals tracking | LOW |
| E | Backend API rate limiting (SlowAPI) | HIGH |
| F | Improve existing admin log viewer / monitoring | MEDIUM |
| G | CI/CD: Docker build + push to GHCR | HIGH |
| H | Production deployment config (Nginx Proxy Manager) | HIGH |
| I | Automated database backups | HIGH |

Out of scope: MFA, external alerting (Grafana/PagerDuty), dedicated log aggregation (ELK/Loki).

---

## P0. Code Quality Fixes (from Verified Codebase Review)

**Prerequisite for all other areas.** These are verified bugs and anti-patterns that must be fixed before production deployment. Full details in `CODEBASE_REVIEW_REPORT.md`.

### P0-Wave 1: Critical & High-Priority (1-2 days)

| # | Issue | Severity | Effort | File | Fix |
|---|-------|----------|--------|------|-----|
| P0.1 | FK type mismatch (Integer→BigInteger) | CRITICAL | 30min | `models/static_sources.py:73` | Change `Column(Integer, ...)` to `Column(BigInteger, ...)` + Alembic migration |
| P0.2 | Missing UNIQUE indexes on materialized views | HIGH | 2hr | Migration + `db/materialized_views.py` | Add UNIQUE indexes to all 4 mat views (required for CONCURRENTLY) |
| P0.3 | Log store race condition | HIGH | 30min | `frontend/src/stores/logStore.ts:152` | Remove `Promise.resolve()` wrapper; update synchronously |
| P0.4 | Health check DB connection leak | HIGH | 30min | `backend/app/main.py:61,221` | Replace `next(get_db())` with existing `get_db_context()` |
| P0.5 | Auth store event listener leak | HIGH | 1hr | `frontend/src/stores/auth.ts:297` | Add cleanup or replace with direct store action call |

### P0-Wave 2: Security & Performance (2-3 days)

| # | Issue | Severity | Effort | File | Fix |
|---|-------|----------|--------|------|-----|
| P0.6 | HTTP-level rate limiting on auth | HIGH | 2hr | `api/endpoints/auth.py` | Add SlowAPI (covered by Area E below, but auth is P0) |
| P0.7 | Composite index on gene_annotations | MEDIUM | 1hr | Migration | `CREATE INDEX ON gene_annotations(gene_id, source)` |
| P0.8 | Bulk mixin bypasses RetryableHTTPClient | MEDIUM | 2hr | `bulk_mixin.py:87,144` | Use source's RetryableHTTPClient for bulk downloads |
| P0.9 | API client missing shared refresh promise | MEDIUM | 2hr | `frontend/src/api/client.ts:49-75` | Implement refresh queue pattern |
| P0.10 | Cache localStorage per request | LOW | 30min | `frontend/src/api/client.ts:33` | Reference auth store token instead |

### P0-Wave 3: Testing & Code Quality (1-2 weeks)

| # | Issue | Severity | Effort | File | Fix |
|---|-------|----------|--------|------|-----|
| P0.11 | Add auth endpoint tests | HIGH | 1 day | `tests/` (new) | Login, refresh, JWT validation, password reset tests |
| P0.12 | Fix get_or_create fixture antipattern | HIGH | 4hr | `tests/fixtures/auth.py:36,49` | Replace with Factory-Boy UserFactory |
| P0.13 | Add @pytest.mark.critical to smoke tests | MEDIUM | 2hr | Various test files | Make `make test-critical` functional |
| P0.14 | Add .dockerignore files | MEDIUM | 30min | Root + frontend | Exclude .git, node_modules, .planning, __pycache__ |
| P0.15 | Replace `any` types with interfaces | MEDIUM | 2-3 days | GeneTable.vue, EnrichmentTable.vue | Define Gene, GeneListMeta, etc. interfaces |
| P0.16 | Lazy-load heavy sub-components | MEDIUM | 2hr | NetworkAnalysis.vue, GeneTable.vue | `defineAsyncComponent()` for NetworkGraph, EnrichmentTable |
| P0.17 | Consolidate log store computed properties | MEDIUM | 1hr | `logStore.ts:79-107` | Single `logStats` computed with one-pass grouping |

### P0-Wave 4: Architecture (Ongoing)

| # | Issue | Severity | Effort | File | Fix |
|---|-------|----------|--------|------|-----|
| P0.18 | Refactor cache_service singleton | MEDIUM | 4hr | `cache_service.py:913-928` | Stateless singleton + request-scoped session binding |
| P0.19 | Consolidate JSON:API response patterns | MEDIUM | 4hr | `api/endpoints/genes.py` | Use ResponseBuilder consistently |
| P0.20 | Centralize pipeline timeout config | LOW | 2hr | `datasource_config.yaml` + sources | YAML-based per-source timeout overrides |
| P0.21 | Extract pipeline error handling mixin | LOW | 3hr | 11 source files | Shared error handling decorator/mixin |
| P0.22 | Standardize admin error patterns | LOW | 1hr | `admin_settings.py` | Use domain exceptions instead of HTTPException |
| P0.23 | Enable pytest-xdist parallelization | MEDIUM | 4hr | `pyproject.toml` | Add pytest-xdist with worker_id DB isolation |

---

## A. Frontend Error Boundaries + Global Error Handling

**Problem:** An unhandled error in any component (especially heavy ones like NetworkGraph, D3 charts, TanStack tables) can blank the entire page.

**What exists:** Nothing. No `onErrorCaptured`, no `app.config.errorHandler`, no `unhandledrejection` listener.

**Plan:**

### A1. Create `ErrorBoundary.vue` component

File: `frontend/src/components/ui/error-boundary/ErrorBoundary.vue`

- Use `onErrorCaptured` to catch child component errors
- Props: `fallbackMessage` (string), optional `onReset` callback
- Show error message + "Try again" button in a styled card (use existing Card + Alert components)
- Log to existing `logService` on capture
- Forward to Sentry/GlitchTip if configured (Area B)
- Return `false` from `onErrorCaptured` to stop propagation

### A2. Wrap high-risk components

Add `<ErrorBoundary>` around:
- `NetworkGraph` in `NetworkAnalysis.vue`
- D3 chart components in `Dashboard.vue` (D3BarChart, D3DonutChart, UpSetChart, etc.)
- `GeneTable` in `Genes.vue`
- `GeneStructureVisualization` and `ProteinDomainVisualization` in `GeneDetail.vue`
- Each admin view's main content area

### A3. Global error handler in `main.ts`

```typescript
app.config.errorHandler = (err, instance, info) => {
  logService.error('Unhandled Vue error', { error: err, info })
  // Forward to Sentry/GlitchTip if initialized
}

window.addEventListener('unhandledrejection', (event) => {
  logService.error('Unhandled promise rejection', { reason: event.reason })
})
```

### A4. Route-level error handling

Add `onError` callback to router for navigation failures (chunk load errors on lazy routes — see Area C).

**Verification:**
- Intentionally throw in a wrapped component → error boundary catches it, page remains functional
- `npm run build` passes
- No console errors during normal operation

---

## B. Frontend Error Reporting (Self-Hosted)

**Problem:** JavaScript errors in production are invisible to operators. The existing `logService` only logs to browser console and in-memory store.

**What exists:**
- `frontend/src/services/logService.ts` — client-side logging with sanitization, levels, correlation IDs
- `frontend/src/stores/logStore.ts` — Pinia store with export, search, filtering
- Backend `system_logs` table + admin log viewer

**Options evaluated:**

| Option | Infra | Sentry SDK compatible | Self-hosted |
|--------|-------|-----------------------|-------------|
| GlitchTip | Postgres + Redis + 2 containers | Yes | Yes |
| Bugsink | Single binary | Yes | Yes |
| Extend logService → backend | None (use existing DB) | No | N/A |

**Recommendation:** Start with **Option 3 (extend logService → backend)** since we already have:
- A `system_logs` table with JSONB context
- Admin log viewer with search, filtering, export
- `logService` with sanitization and levels

Then optionally add GlitchTip later if volume/features demand it.

### B1. Add frontend error reporting endpoint

File: `backend/app/api/endpoints/client_logs.py`

- `POST /api/client-logs` — public endpoint (no auth required), accepts:
  - `level`, `message`, `error_type`, `error_message`, `stack_trace`
  - `url`, `user_agent`, `context` (JSONB)
- Rate-limited: 20/minute per IP (prevent abuse)
- Writes to existing `system_logs` table with `logger='frontend'`
- Minimal validation via Pydantic schema

### B2. Extend logService to report errors to backend

File: `frontend/src/services/logService.ts`

- For `ERROR` and `CRITICAL` levels: POST to `/api/client-logs`
- Use `navigator.sendBeacon()` for reliability (fires even on page unload)
- Batch errors (max 1 request per 5 seconds, queue up to 10)
- Include: URL, user agent, app version, error stack trace
- Respect existing sanitization (strip auth tokens, passwords)

### B3. Add frontend log source filter to admin log viewer

- Add "frontend" as a filterable source in `AdminLogViewer.vue`
- Show URL and user agent in log detail modal

**Verification:**
- Trigger a frontend error → appears in admin log viewer within 10 seconds
- `sendBeacon` fires on page close with queued errors
- No PII leaks in reported errors

---

## C. Route-Level Code Splitting + Lazy Loading

**Problem:** All routes and heavy components load upfront. With 5,080+ genes, admin panel, network visualization, and D3 charts, the initial bundle is unnecessarily large.

**What exists:** All routes use direct imports in `frontend/src/router/index.ts`. No lazy loading.

**Reference:** Phentrieve uses `manualChunks` in vite.config + lazy routes.

### C1. Convert all routes to lazy imports

File: `frontend/src/router/index.ts`

```typescript
// Before
import Home from '@/views/Home.vue'
// After
const Home = () => import('@/views/Home.vue')
```

Group by access pattern:
- **Eager (keep direct import):** App shell layout only (AppHeader, AppFooter)
- **Lazy — public routes:** Home, About, DataSources, Dashboard, Genes, GeneDetail, GeneStructure, NetworkAnalysis, Profile
- **Lazy — auth routes:** Login, Register (if separate pages exist)
- **Lazy — admin routes:** All 11 admin views (already behind auth guard)

### C2. Use `defineAsyncComponent` for heavy sub-components

Wrap components that are large or conditionally rendered:
- `NetworkGraph` (~1,619 lines, only on network page)
- `GeneStructureVisualization` (~799 lines, only on gene detail)
- `ProteinDomainVisualization` (~773 lines, only on gene detail)
- `UpSetChart` (~557 lines, only on dashboard)
- `ClusterDetailsDialog` (only on network page, on click)

Provide loading placeholder (skeleton) and error fallback.

### C3. Configure Vite manual chunks

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

This separates rarely-changing vendor code from app code for better cache hit rates.

### C4. Add chunk load error recovery

When a lazy chunk fails to load (network error, deploy during navigation), catch the error and offer reload:

```typescript
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module')) {
    window.location.href = to.fullPath  // Full page reload to get new chunks
  }
})
```

**Verification:**
- `npm run build` succeeds
- Network tab shows chunks loading on-demand (not all upfront)
- Bundle analyzer shows vendor chunks separated
- Navigate to admin → admin chunk loads only then
- Simulate chunk load failure → user sees reload prompt, not blank page

---

## D. Web Vitals Tracking

**Problem:** No visibility into real-user performance (LCP, CLS, INP, FCP, TTFB).

**Plan:**

### D1. Install and configure `web-vitals`

```bash
cd frontend && npm install web-vitals
```

File: `frontend/src/utils/web-vitals.ts`

- Import `onCLS`, `onINP`, `onLCP`, `onFCP`, `onTTFB` from `web-vitals`
- In production: send via `navigator.sendBeacon` to `/api/client-logs` with `logger='web-vitals'`
- In development: `console.log` only
- Include: metric name, value, rating (good/needs-improvement/poor), page path

### D2. Initialize in `main.ts` after app mount

### D3. Add Web Vitals section to admin dashboard (optional)

- Query `system_logs` where `logger='web-vitals'`
- Show average LCP, CLS, INP over last 24h/7d
- Color-code by rating thresholds

**Verification:**
- Navigate several pages → vitals appear in admin log viewer
- No performance impact from tracking itself

---

## E. Backend API Rate Limiting

**Problem:** No per-IP or per-user request limits. Any client can hammer the API without restriction.

**What exists:**
- Rate limiting for *outbound* API calls (pipeline sources) via `SimpleRateLimiter`
- Redis already available (used by ARQ worker)

**Reference:** Phentrieve notes "configure rate limiting in production" but hasn't implemented it yet. We'll be ahead.

### E1. Install SlowAPI

```bash
cd backend && uv add slowapi
```

### E2. Create rate limiting module

File: `backend/app/core/rate_limit.py`

- Key function: per-user (if authenticated via JWT) or per-IP (if anonymous)
- Default limits: `200/minute`, `5000/hour`
- Storage: Redis (reuse existing Redis from ARQ, different DB number)
- Fallback: in-memory if Redis unavailable

### E3. Register middleware in `main.py`

- Add `SlowAPIMiddleware`
- Add `RateLimitExceeded` exception handler → 429 JSON response with `Retry-After` header

### E4. Apply per-endpoint overrides

| Endpoint pattern | Limit | Rationale |
|-----------------|-------|-----------|
| `POST /api/auth/login` | 5/minute | Brute-force protection |
| `POST /api/auth/register` | 3/minute | Abuse prevention |
| `GET /api/genes` | 60/minute | Allow browsing, prevent scraping |
| `GET /api/genes/{id}` | 120/minute | Detail page, higher limit |
| `POST /api/annotations/pipeline/*` | 2/minute | Heavy operations |
| `POST /api/admin/*` | 30/minute | Admin operations |
| `POST /api/client-logs` | 20/minute | Frontend error reporting (Area B) |
| `GET /api/statistics/*` | 30/minute | Computed endpoints |
| All other `GET` | 200/minute (default) | General reads |
| All other `POST/PUT/DELETE` | 60/minute | General writes |

### E5. Add rate limit headers to responses

- `X-RateLimit-Limit`: current limit
- `X-RateLimit-Remaining`: remaining requests
- `X-RateLimit-Reset`: reset timestamp

### E6. Add rate limit info to admin dashboard

- Show current rate limit stats (top consumers, blocked requests)
- Query from Redis keys

**Verification:**
- Exceed login limit → 429 with Retry-After header
- Normal browsing → no rate limit hits
- `make test` passes (tests bypass rate limiting via test client)

---

## F. Improve Admin Log Viewer / Monitoring

**Problem:** The existing system is solid but could surface more actionable insights.

**What exists (comprehensive):**
- `AdminLogViewer.vue`: Search, filter by level/source/time/request ID, pagination, export, cleanup
- `LogHealthMonitor`: Error rate checking, performance checking, critical pattern detection
- `LogMaintenance`: Auto-cleanup, volume monitoring, table optimization
- `CacheMonitoringService`: Hit rates, health checks, Prometheus endpoint
- WebSocket real-time pipeline progress

**Plan (incremental improvements):**

### F1. Add frontend error log tab

- New tab or filter preset in `AdminLogViewer.vue` for `logger='frontend'` logs
- Show URL, user agent, stack trace prominently
- Group by error type for deduplication

### F2. Add simple uptime widget to admin dashboard

- `AdminDashboard.vue`: Add a card showing:
  - API uptime (calculated from health check history in `system_logs`)
  - Last restart timestamp
  - Current request rate (requests/min from recent logs)
- No external service needed — derive from existing log data

### F3. Add error rate sparkline to admin dashboard

- Small inline chart (reuse D3BarChart pattern) showing errors/hour over last 24h
- Red threshold line at configured error rate limit

### F4. Add log retention settings to admin settings

- Allow configuring retention days from the admin Settings page
- Currently hardcoded in `LogMaintenance` — make it a `settings` table entry

**Verification:**
- Frontend errors appear in admin viewer with source filter
- Dashboard shows uptime and error rate
- Retention setting change takes effect on next cleanup cycle

---

## G. CI/CD: Docker Build + Push to GHCR

**Problem:** CI runs tests but never builds or publishes Docker images. Deployment is manual.

**What exists:**
- `.github/workflows/ci.yml` — lint, test, coverage
- `.github/workflows/security.yml` — Bandit, pip-audit, npm audit
- `.github/workflows/trivy-security-scan.yml` — container scanning
- `Dockerfile` for backend and frontend (production-hardened)
- `docker-compose.prod.yml` — production compose

**Reference:** Phentrieve's `docker-publish.yml` — dual-image GHCR push with semver tagging, Hadolint, Trivy, Dockle.

### G1. Create `.github/workflows/cd.yml`

Trigger: push to `v*` tags + manual `workflow_dispatch`

**Jobs:**

1. **lint-dockerfiles** — Hadolint on both Dockerfiles
2. **build-backend** — Build + push `ghcr.io/<repo>/backend` with semver tags
3. **build-frontend** — Build + push `ghcr.io/<repo>/frontend` with semver tags
4. **scan** — Trivy + Dockle on built images, SARIF upload to GitHub Security
5. **deploy** (optional, requires `production` environment) — SSH to server, pull + restart

**Tagging strategy** (match phentrieve):
- `v1.2.3` → tags: `1.2.3`, `1.2`, `1`, `latest`
- Commit SHA short tag for traceability
- Use `docker/metadata-action@v5` for automatic tag generation

**Caching:**
- `cache-from: type=gha` + `cache-to: type=gha,mode=max` for layer caching
- Registry-based cache as fallback

**Permissions:**
- `contents: read`, `packages: write` for GHCR push
- `security-events: write` for SARIF upload

### G2. Add deployment protection

- Create GitHub Environment `production` with required reviewers
- Deploy job requires environment approval before running

### G3. Add deploy step

Two options (choose based on preference):

**Option A: SSH deploy** (like phentrieve)
- `appleboy/ssh-action@v1` to SSH into server
- Pull new images, `docker compose up -d`, prune old images

**Option B: Watchtower** (auto-pull)
- Run Watchtower container on production server
- Watches GHCR for new image tags, auto-restarts
- No SSH secrets needed in GitHub

**Verification:**
- Push a `v*` tag → images appear in GHCR packages
- Trivy scan results in GitHub Security tab
- Deploy updates running containers on server

---

## H. Production Deployment Config (Nginx Proxy Manager)

**Problem:** `docker-compose.prod.yml` uses `npm_proxy_network` but no setup documentation exists.

**What exists:**
- `docker-compose.prod.yml` — hardened, no exposed ports, expects external proxy
- `docker-compose.prod.test.yml` — test variant with localhost ports
- Frontend nginx.conf with security headers, gzip, SPA routing

**Plan:**

### H1. Document Nginx Proxy Manager setup

File: `docker-compose.prod.yml` (add comments) + section in README or CLAUDE.md

Document:
- NPM network creation: `docker network create npm_proxy_network`
- Proxy host config for frontend (port 8080) and backend API (port 8000)
- SSL certificate via Let's Encrypt (NPM handles this)
- WebSocket support for `/api/progress/ws`
- Custom locations: `/api` → backend:8000, `/` → frontend:8080
- Advanced nginx config for WebSocket upgrade headers

### H2. Add `env-config.js` for runtime frontend config

The frontend needs the API URL at runtime (not build time) when deployed behind a proxy.

File: `frontend/public/env-config.js`
- Loaded via `<script>` in `index.html`
- Sets `window.__ENV__` with `VITE_API_URL`, `VITE_SENTRY_DSN`, etc.
- The nginx container serves this file with `no-cache` headers
- Already partially in place — verify and document

### H3. Add production checklist

Document in `.planning/` or inline comments:
- [ ] Create Docker network: `docker network create npm_proxy_network`
- [ ] Copy `.env.production.example` → `.env.production`, fill secrets
- [ ] `docker compose -f docker-compose.prod.yml up -d`
- [ ] Configure NPM proxy hosts (frontend + API)
- [ ] Request SSL certificates via NPM
- [ ] Verify health endpoints: `/health` (frontend), `/health` (backend)
- [ ] Create initial admin user
- [ ] Run initial data pipeline via API
- [ ] Verify WebSocket connection for pipeline progress

**Verification:**
- Fresh deployment following checklist → site accessible via HTTPS
- WebSocket pipeline progress works through NPM proxy
- Health checks pass

---

## I. Automated Database Backups

**Problem:** `BackupService` exists with pg_dump/restore, checksums, and compression — but no scheduling.

**What exists:**
- `backend/app/services/backup.py` — Full backup service with:
  - pg_dump with compression
  - SHA256 checksum verification
  - Safety backup before restore
  - Post-restore ANALYZE
- `POST /api/admin/backups/create` — Manual trigger via API
- `GET /api/admin/backups/list` — List existing backups

### I1. Add backup sidecar container

Add to `docker-compose.prod.yml`:

```yaml
db-backup:
  image: prodrigestivill/postgres-backup-local:16
  depends_on:
    db:
      condition: service_healthy
  environment:
    POSTGRES_HOST: db
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

### I2. Add backup volume to compose

Add `db-backups` named volume for persistence across container restarts.

### I3. Add backup health check to admin dashboard

- Show last backup timestamp and size
- Warning if no backup in >26 hours
- Read from backup volume or sidecar healthcheck endpoint

### I4. Document backup restore procedure

- How to list backups in the volume
- How to restore from a specific backup
- How to verify restore integrity
- Emergency procedure: restore from backup when DB is corrupted

**Verification:**
- Sidecar starts and creates first backup at scheduled time
- Backup files appear in volume with expected naming
- Old backups are rotated per retention policy
- Restore from backup works on test instance

---

## Implementation Order

Recommended execution sequence based on dependencies and impact:

```
P0-Wave 1 (CRITICAL — must complete first):
  ├── P0.1: FK type mismatch fix + migration
  ├── P0.2: Materialized view UNIQUE indexes + migration
  ├── P0.3: Log store race condition fix
  ├── P0.4: Health check connection fix
  └── P0.5: Auth store listener leak fix

P0-Wave 2 (HIGH — security & performance, parallelizable):
  ├── P0.6+E: API rate limiting (auth + general — combined)
  ├── P0.7: Composite index migration
  ├── P0.8: Bulk mixin RetryableHTTPClient
  ├── P0.9: API client refresh queue
  └── P0.14: .dockerignore files

Wave 1 (independent, can parallelize with P0-Wave 2):
  ├── C: Route-level code splitting (frontend, no backend changes)
  ├── I: Automated backups (docker-compose only)
  └── P0.10-P0.17: Remaining code quality items

Wave 2 (builds on Wave 1):
  ├── A: Error boundaries (frontend, uses patterns from C)
  ├── G: CI/CD pipeline (needs stable Dockerfiles + .dockerignore)
  └── H: Production deployment docs (needs stable compose)

Wave 3 (builds on Wave 2):
  ├── B: Frontend error reporting (needs A for error capture)
  ├── F: Admin log viewer improvements (needs B for frontend logs)
  └── D: Web Vitals tracking (needs B for reporting endpoint)

Ongoing (no blocking dependencies):
  ├── P0.18-P0.23: Architecture improvements
  └── Test coverage expansion
```

**Estimated effort:** ~5-8 sessions total across all waves (P0 adds ~2-3 sessions).

---

## Excluded (with rationale)

| Item | Reason |
|------|--------|
| MFA | Overkill for current user base |
| External alerting (Grafana, PagerDuty) | Overkill — admin dashboard sufficient |
| Log aggregation (ELK, Loki) | Existing DB-backed log viewer is adequate |
| Database HA / replication | Single-instance sufficient for current scale |
| CDN | NPM handles SSL termination; static assets are small |
| Feature flags | Can add later if needed; redeployment is fast |
| GlitchTip/Sentry self-hosted | Start with extending existing logService; add later if needed |

---

*Plan created: 2025-03-10*
*Updated: 2026-03-10 — Integrated verified codebase review findings as P0 prerequisites*
*Status: DRAFT — ready for review*
