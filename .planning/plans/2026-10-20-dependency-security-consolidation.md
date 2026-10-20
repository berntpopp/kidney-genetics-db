# Dependency and security consolidation

Goal: consolidate the 17 currently open Dependabot updates and remediate the open dependency and container findings in one reviewable PR.

Scope and ownership:
- Frontend: package manifest and npm-generated lockfile; necessary compatibility changes and existing lint, format, Vitest, build, and npm audit checks.
- Python: backend, MCP, and literature scraper manifests and uv-generated locks; existing component and security checks. Preserve Python 3.13 development baseline and MCP read-only contract.
- Infrastructure: action versions and container references/configuration, with workflow and Compose validation and investigation of Trivy findings.
- Integration: review all changes, verify each requested update and alert against available patched versions, run the root quality gate, and publish one PR with exact results and remaining blockers.

Constraints: preserve unrelated `.ua/` files; no production operations, database resets, alert suppression, invented versions, manual lockfile edits, or unrelated modernization. Major upgrades require compatibility verification. Use isolated test services if database tests need them.

Execution:
- [x] Inventory live PRs and open security alerts using GitHub API.
- [x] Apply compatible dependency and infrastructure fixes in disjoint parallel work areas.
- [x] Review diffs and run component and root checks, recording unavailable patches or services.
- [ ] Publish a single PR documenting superseded updates and security coverage.

Verification and decisions:
- `make check` passed against a disposable migrated PostgreSQL database: backend 691 passed/10 skipped, frontend 116 passed, MCP 204 passed; lint, formatting, build, strict mypy and contract verification passed.
- `npm ci`, `npm ls --all`, and `npm audit --json` passed; npm audit found zero vulnerabilities. All 41 GitHub frontend alerts were checked against every resolved version.
- Backend `uv run pip-audit --local --format json`; MCP and literature `uv tool run pip-audit --path .venv/lib/python3.13/site-packages --format json` with separate temporary audit caches all passed with zero known vulnerabilities in audited third-party dependencies. All 77 GitHub Python alerts were checked against every locked version, including Python marker branches.
- Literature PDF text/line/table extraction and BeautifulSoup CSS selection smoke checks passed. Its optional Ruff check still reports three existing unused imports in `literature_scraper_individual.py`; no source changes were needed.
- Workflow `actionlint`, new PostgreSQL Dockerfile `hadolint`, all four `docker compose -f <file> config --quiet` checks, and `git diff --check` passed.
- The official PostgreSQL 17.11 Alpine 3.24 digest still has unpatched zlib. A small pinned Dockerfile upgrades only zlib to 1.3.2-r1. All Compose PostgreSQL services and the PostgreSQL scan build this same image; volumes and PostgreSQL major remain unchanged. A local build and isolated database startup/write/read smoke check passed. No production service was changed.
- Unfiltered Trivy 0.76 scan of the patched image reports zero OS vulnerabilities; all 29 open code-scanning CVE IDs are absent. Its existing gosu binary still has 60 Go findings; the pre-existing workflow path exclusion is unchanged. CI's disposable service uses the refreshed official image because GitHub service containers start before build steps.
- Live dependency PRs incorporated: #277, #276, #274, #273, #272, #271, #269, #267, #265, #263, #260, #258, #245, #236, #235, #232. Actual live titles differ from the pasted list.
- #230 (TypeScript 7) remains blocked: latest stable @typescript-eslint/parser 8.72.0 and canary require TypeScript >=4.8.4 <6.1.0. npm rejects installation with ERESOLVE. Retain compatible TypeScript 6 rather than forcing unsupported peers.
- GitHub security dashboards require merge and fresh default-branch dependency/scan processing before closing alerts. No alerts were dismissed or newly suppressed. Browser E2E and production deployment were not run.
- Repeated `uv run alembic upgrade head` and `make check-backend` against the actual patched PostgreSQL 17.11 image: migration passed; 691 tests passed, 10 skipped. Independent agents reviewed frontend, Python, actions, container/volume compatibility and scan identity; no actionable findings remained.
