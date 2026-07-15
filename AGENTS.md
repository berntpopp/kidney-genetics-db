# Kidney-Genetics Database Agent Guide

This is the durable, shared instruction source for every coding agent in this repository. Tool-specific instruction files must be thin bridges to this guide.

## Project Context

- Kidney-Genetics Database is a scientific platform for curating and exploring kidney-disease genes and their supporting evidence.
- It combines FastAPI/PostgreSQL, Vue, read-only FastMCP, operational scrapers, Docker Compose infrastructure, and planning records.
- Treat curation, provenance, reproducibility, privacy, and schema integrity as product requirements; cosmetic speed never overrides them.
- Work from the current repository state and preserve unrelated user changes.
- `AGENTS.md` is the cross-LLM source of truth. `CLAUDE.md` stays minimal so Claude Code imports this guide instead of duplicating it.

## Repository Map

- `backend/` contains the FastAPI service, SQLAlchemy models, Alembic history, annotation pipeline, ARQ worker, tests, and a `uv.lock`.
- `backend/app/api/` owns endpoints, `app/services/` business logic, `app/core/` shared infrastructure, and `app/pipeline/` ingestion.
- `frontend/` is the Vue 3, TypeScript, Vite, Tailwind, shadcn-vue, and Pinia application; `frontend/package-lock.json` is its deterministic lockfile.
- `frontend/src/api/`, `src/stores/`, and `src/components/ui/` respectively own API clients, Pinia state, and shadcn-vue primitives.
- `mcp/` is the independently locked, read-only FastMCP server; local commands live in `mcp/Makefile`.
- `mcp/contract/` holds the OpenAPI snapshot; generated contract modules live in `mcp/src/kidney_genetics_mcp/contract/`.
- `scrapers/literature/` is an independent locked `uv` project.
- `scrapers/diagnostics/` is an operational tool with a lint-only `pyproject`: it declares no dependencies and has no lockfile or test gate. It is excluded from root install/check pending a dedicated packaging task.
- `docker-compose.yml` runs the full development stack;
  `docker-compose.services.yml` runs PostgreSQL and Redis for hybrid work.
- `docker-compose.prod.yml` and `docker-compose.prod.test.yml` describe
  production and production-test environments.
- `.planning/specs/` and `.planning/plans/` hold durable design and execution records. Treat `.planning/archive/` as historical evidence, not live code.
- `.github/workflows/` defines CI, security, release, and deployment checks.

## Prerequisites and Setup

- Python 3.13 is the local-development and CI baseline; metadata may support a wider range, but do not change this baseline casually.
- The backend production image intentionally uses Python 3.14; that does not alter the local or CI baseline.
- Use Node.js >=22.18.0 for the frontend and current `uv`, Docker Engine, and Docker Compose v2. Invoke Compose as `docker compose`.
- Copy only required examples: root `.env.example`, `backend/.env.example`, or
  `mcp/.env.example`. Never commit populated `.env` files or expose values.
- This modernization introduces `make install` as the deterministic root bootstrap: locked Python dependency sync for backend/MCP and `npm ci` for frontend.
- On a branch or revision predating that target, use `cd backend && uv sync --locked --group dev`, `cd frontend && npm ci`, and `cd mcp && uv sync --locked --group dev` instead.
- `make hybrid-up` starts PostgreSQL and Redis for local services; use `make dev-up` for the full Docker stack. Use `make help` for target details.
- Check tooling before debugging setup: `uv --version`, `node --version`,
  `npm --version`, and `docker compose version`.

## Common Commands

On revisions defining them, root Makefile targets are the stable interface;
prefer them to recreating long command sequences in shells, CI, or agent prompts.

```bash
make install                  # deterministic setup (when this target exists)
make check                    # non-mutating root quality gate (when it exists)
make help                     # list operational targets
make hybrid-up                # PostgreSQL + Redis for local services
make backend                  # FastAPI on http://localhost:8000
make frontend                 # Vite development server
make worker                   # ARQ worker (requires Redis)
make mcp                      # read-only MCP server (requires backend API)
make hybrid-down              # stop hybrid services
make dev-up                    # start the full Docker stack
make dev-down                  # stop the full Docker stack
```

Run the narrowest command that proves the changed behavior before escalating.

```bash
cd backend && uv run ruff check --no-fix app/    # backend lint, no rewrite
cd backend && uv run ruff format --check app/    # backend formatting
cd backend && uv run pytest tests/ -v            # backend test suite
cd backend && uv run ruff check --fix app/       # explicit backend lint fixes
cd frontend && npm run lint:check && npm run format:check
cd frontend && npm run test:run && npm run build
make -C mcp check                                # ruff, strict mypy, pytest
make -C mcp contract-verify                      # regenerate and detect drift
docker compose -f docker-compose.yml config      # Compose validation
git diff --check                                 # whitespace/conflict check
```

- `make check` and `*:check` commands are verification-only. On revisions that
  predate the root target, run all affected focused checks; use fix commands
  only after review.
- Database changes use Alembic: create and review a revision, then apply it via
  `cd backend && uv run alembic upgrade head` in the intended environment.
- Do not run destructive reset, cleanup, rebuild, release, or production
  targets without explicit authorization for their side effects.

## Development Boundaries

- Never commit secrets, tokens, credentials, private data, local `.env` files,
  or copied production configuration.
- Never alter, stage, revert, delete, or format unrelated user work. Inspect
  `git status --short` before and after work and stage by path.
- Never hand-edit generated or cached artifacts. Change their source and run
  the documented generator; update locks only through package tooling.
- Never declare a database schema change complete without a reviewed Alembic
  migration. Model-only changes and manual database edits are insufficient.
- Never run annotation updates or pipelines through ad hoc Python scripts; use
  the API endpoints that own sessions, progress, recovery, and authorization.
- For pipeline work, use `/api/annotations/pipeline/` endpoints such as
  `update`, `update-failed`, `update-new`, `update-missing/{source}`, or `status`.
- Before adding an abstraction, confirm its public symbol and reuse
  `get_logger`/`UnifiedLogger`, `CacheService`, `retry_with_backoff`/
  `RetryableHTTPClient`, and `BaseAnnotationSource` where responsibilities fit.
- Do not bypass API, service, database, authorization, or validation layers to
  make an isolated feature appear to work.
- Preserve scientific source provenance and identifiers; never invent data,
  annotations, citations, counts, names, or source claims.
- Ask for direction before changing public API behavior, data semantics, or
  production state beyond the assigned task.

## Component Conventions

### Backend

- Keep FastAPI routers thin: validate and authorize at the API boundary, keep
  business rules in services, and keep persistence behind models/CRUD layers.
- Add schema changes through Alembic revisions and verify upgrade behavior.
- Extend annotation sources from `BaseAnnotationSource`; reuse existing logging,
  cache, retry, HTTP-client, and source abstractions after confirming contracts.
- Do not place blocking I/O or CPU-heavy work on the event loop when a worker
  or executor boundary already exists.
- Prefer API-driven operations over direct scripts so transactions, progress,
  retries, auditing, and permissions remain consistent.

### Frontend

- Use `frontend/src/api/` modules for backend access; never put ad hoc raw
  `fetch` or Axios calls in views and components.
- Put shared client state in Pinia stores and reusable behavior in composables;
  keep views focused on composition and route interaction.
- Prefer existing shadcn-vue primitives under `src/components/ui/` and preserve
  their accessibility and Tailwind conventions.
- Pair API contract changes with typed client, view/store, and focused Vitest
  coverage where frontend behavior changes.

### MCP

- MCP is read-only: proxy only the code-enforced allowlist of side-effect-free
  public `GET` paths. Never add write, admin, auth, pipeline, staging, or
  arbitrary URL access.
- Treat the OpenAPI snapshot and generated contract package as coupled. Run
  `make -C mcp contract`; never hand-edit `_generated_*.py`.
- Preserve strict mypy, contract-drift, response-shaping, and citation
  provenance behavior when extending tools or clients.

### Scrapers, Compose, and Planning

- Keep dependencies and execution inside the scraper that owns them. Do not add
  `scrapers/diagnostics` to root installation or CI until packaging, locking,
  and a test gate exist.
- Run a Compose config check after Compose edits. Keep values in examples or
  local untracked files, never embedded credentials.
- Record significant designs and executable plans in `.planning/specs/` and
  `.planning/plans/`; do not rewrite archive records to alter history.

## Testing and Verification

- Run focused verification first, then the component check. Where defined, run
  `make check` before handoff for cross-component or shared-tooling work.
- Backend integration, pipeline, and operational tests may need PostgreSQL and
  Redis from `make hybrid-up`; report that dependency rather than masking it.
- Frontend changes normally need applicable lint, format, Vitest, and build
  commands. MCP changes need `make -C mcp check`; contract changes also need
  `make -C mcp contract-verify` and review of regenerated artifacts.
- Documentation-only work at minimum needs `git diff --check` plus command/link
  review. Configuration needs its narrowest consumer parser or validator.
- Failures are evidence, not noise: diagnose root cause, preserve regression
  coverage, and state exact remaining failures.
- If a check cannot run, report the complete command, exit status, blocker,
  affected scope, and what was verified instead.
- Do not claim a change is complete, correct, secure, or passing without fresh
  command output covering that claim.

## Multi-Agent and Handoff Workflow

- Keep durable instructions here; tool-specific instruction files import this
  guide rather than maintaining divergent copies.
- Read the nearest applicable `AGENTS.md`. Add a nested guide only for
  genuinely different durable rules.
- Split parallel work by disjoint write sets. Assign file ownership explicitly;
  no two agents edit one file without an integration owner.
- Inspect the working tree before edits; treat uncommitted or untracked files
  outside scope as another contributor's work.
- Every handoff states the goal, changed files, verification commands/results,
  remaining risks or blockers, and required follow-up.
- Keep commits cohesive and scoped. Integrate intentionally and never hide
  merge conflicts with broad rewrites or unrelated formatting.
- Review another agent's diff and run relevant checks yourself; a report is
  context, not proof.

## Pull Request Expectations

- Use Conventional Commits: `type(scope): imperative summary`, for example
  `feat(mcp): add evidence lookup` or `docs: clarify local setup`.
- Keep the pull request focused. Explain behavioral, scientific, operational,
  migration, and contract impact, and why the chosen boundary is safe.
- List exact verification commands and results; distinguish blocked checks from
  passing checks.
- Call out migrations, generated contracts, dependency locks, Compose changes,
  environment requirements, and unavailable external services or credentials.
- Never include unrelated user work, secrets, hand-edited generated files, or
  unreviewed bulk reformatting.
