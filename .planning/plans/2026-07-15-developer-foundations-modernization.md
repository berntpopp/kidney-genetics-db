# Developer Foundations Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository reproducible and safe to develop with any major coding agent by centralizing instructions, adding deterministic root commands, aligning CI, and correcting onboarding documentation.

**Architecture:** `AGENTS.md` is the durable, tool-neutral authority; `CLAUDE.md` only imports it. The root Makefile orchestrates the independently locked backend, frontend, and MCP projects. CI invokes the same focused gates.

**Tech Stack:** Python 3.13 local/CI baseline with uv, Node >=22.18.0 with npm, Docker Compose v2, FastAPI, Vue/Vite, FastMCP, GitHub Actions, GNU Make.

---

## Task 1: Add shared cross-LLM guidance

**Files:** Create `AGENTS.md`; modify `CLAUDE.md`.

- [x] **Step 1: Write the failing layout check.** Run `test -f AGENTS.md`; it must fail before implementation.
- [x] **Step 2: Create the guide.** Add `AGENTS.md` with exact sections: Project Context; Repository Map; Prerequisites and Setup; Common Commands; Development Boundaries; Component Conventions; Testing and Verification; Multi-Agent and Handoff Workflow; Pull Request Expectations. It must document backend/frontend/MCP/scrapers/Compose/`.planning`, Python 3.13 local/CI, Node >=22.18.0, backend production Python 3.14, Docker Compose v2, component lockfiles, API-mediated pipelines, Alembic, existing core utilities, MCP contract generation, generated-data and secret rules, conventional commits, and agent handoffs. State that `scrapers/diagnostics` is excluded from root installation/checks until it declares dependencies and tests.
- [x] **Step 3: Replace `CLAUDE.md` exactly.** Its five lines must be: heading `# Claude Code Instructions`; blank line; `Read and follow \`AGENTS.md\` for all repository guidance.`; blank line; `@AGENTS.md`.
- [x] **Step 4: Verify.** Run `test -f AGENTS.md`; `test "$(wc -l < CLAUDE.md)" -eq 5`; `rg -n '^@AGENTS\\.md$' CLAUDE.md`; `! rg -n 'Current Status.*v0\\.2\\.0|There is no separate \`docs/\` directory' CLAUDE.md AGENTS.md`; and `git diff --check`. All must succeed.
- [x] **Step 5: Commit.** Run `git add AGENTS.md CLAUDE.md` then `git commit -m "docs: add shared agent guidance"`.

## Task 2: Add deterministic root commands

**Files:** Modify `Makefile`.

- [x] **Step 1: Write the failing behavior check.** Run `make -n lint | rg 'ruff check app/ --fix'`; it proves the existing validation target mutates source.
- [x] **Step 2: Add locked bootstrap targets.** Add `install` depending on `install-backend install-frontend install-mcp`. The backend and MCP recipes are `uv sync --locked --group dev` in their directories; the frontend recipe is `npm ci` in `frontend/`. Include all in `.PHONY`; make `mcp-build` a compatibility alias for `install-mcp`.
- [x] **Step 3: Add non-mutating checks.** `check` depends on `check-backend check-frontend check-mcp`. Backend check runs `uv lock --check`, `ruff check --no-fix app/`, `ruff format --check app/`, and `pytest tests/ -v`. Frontend check runs `npm run lint:check`, `npm run format:check`, `npm run build`, and `npm run test:run`. MCP check runs `uv lock --check`, `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest`, then the read-only `make -C mcp contract-verify`.
- [x] **Step 4: Make mutation explicit.** Change `lint` to checking only. Add `lint-fix` for backend `ruff check --fix` and frontend `npm run lint`; add `format` for backend/MCP `ruff format` and frontend `npm run format`; include MCP in `format-check`. Define `ci-backend`, `ci-frontend`, and `ci-mcp` as wrappers and make `ci` depend on all three. Preserve legacy test/service/database targets.
- [x] **Step 5: Update help and verify target shape.** `make help` must list bootstrap, checks, explicit fixes, and the database requirement for backend checks. Run `make -n install`, `make -n check`, every focused check dry-run, `! make -n lint | rg -- '--fix'`, `make -n lint-fix | rg -- '--fix'`, and `make -n format-check | rg 'cd mcp && uv run ruff format --check \\.'`.
- [x] **Step 6: Run database-free checks.** Run `make check-frontend` and `make check-mcp`; both must pass.
- [x] **Step 7: Commit.** Run `git add Makefile` then `git commit -m "build: add deterministic development commands"`.

## Task 3: Align CI with local commands

**Files:** Modify `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `.github/workflows/lighthouse.yml`.

- [x] **Step 1: Write the failing CI check.** Run `! rg -n 'mcp-ci|MCP CI' .github/workflows/ci.yml`; it succeeds because MCP is currently absent.
- [x] **Step 2: Add MCP CI.** Add `mcp` to changes outputs and `dorny/paths-filter`, matching `mcp/**`, `Makefile`, and `.github/workflows/ci.yml`. Add `mcp-ci`, conditional on the filter, with `astral-sh/setup-uv@v7` caching `mcp/uv.lock`, `actions/setup-python@v6` at Python 3.13, locked MCP sync, then `make check-mcp` from root. Add MCP to `ci-summary` needs, Markdown table, and failure handling.
- [x] **Step 3: Align dependency/runtime commands.** Change backend CI sync to `uv sync --locked --group dev`. Replace frontend `node-version: '22'` in CI, security, and Lighthouse with `node-version: '22.18.x'`; keep the compatible Node 26 Docker builder.
- [x] **Step 4: Verify workflow content.** Parse every workflow through `yaml.safe_load` using `backend`'s uv environment; then search `.github/workflows` for `mcp-ci`, `mcp/**`, locked sync, and the 22.18.x Node range. Expect all assertions to pass.
- [x] **Step 5: Commit.** Run `git add .github/workflows/ci.yml .github/workflows/security.yml .github/workflows/lighthouse.yml` then `git commit -m "ci: verify MCP and locked dependencies"`.

## Task 4: Refresh onboarding and component documentation

**Files:** Modify `README.md`, `backend/README.md`, `backend/TESTING.md`, `frontend/README.md`, `mcp/README.md`.

- [x] **Step 1: Replace root setup guidance.** Document Git; Docker Compose v2; uv; Python 3.13 local/CI with backend production Python 3.14; Node >=22.18.0; and the sequence `make install`, `cp backend/.env.example backend/.env` plus its required backend settings, `make hybrid-up`, `cd backend && uv run alembic upgrade head`, `make backend`, `make frontend`, optional `make worker`, optional `make mcp`. State that `make services-up` precedes backend checks, list check/CI/security commands, set static version/citation text to 0.5.1, and link `AGENTS.md`.
- [x] **Step 2: Use one component install model.** Component READMEs use `make install-backend`, `make install-frontend`, and `make install-mcp`; local alternatives use locked uv sync or `npm ci`, never bare `npm install`, `uv sync --dev`, or bare `pytest`. Replace generic frontend documentation with project run/build/test/E2E guidance. Make backend testing recommend Docker PostgreSQL plus `make services-up` and `make check-backend`, not system Postgres build packages.
- [x] **Step 3: Preserve an honest scraper boundary.** Root README and `AGENTS.md` must say diagnostics is a legacy utility without a dependency manifest, lockfile, or test gate and is therefore excluded from root install/check until a dedicated packaging modernization.
- [x] **Step 4: Verify and commit.** Run `! rg -n 'Node\\.js 18\\+|Python 3\\.14\\+|uv sync --dev|npm install' README.md backend/README.md backend/TESTING.md frontend/README.md mcp/README.md AGENTS.md`; search README/AGENTS for all four new command families; verify README contains `0.5.1`; run `git diff --check`; then commit with `docs: document reproducible development setup`.

## Task 5: Remove obsolete Compose metadata and run complete verification

**Files:** Modify `docker-compose.yml`, `docker-compose.services.yml`.

- [x] **Step 1: Remove obsolete Compose references.** Remove the obsolete `version: '3.8'` keys and stale mounts of the absent `init.sql` file from both Compose files; retain all real service configuration.
- [x] **Step 2: Validate Compose without warnings.** Run `docker compose -f docker-compose.yml config --quiet` and the services variant, each redirecting stderr to a temporary file; both files must be empty. Remove the temporary files.
- [x] **Step 3: Run full checks.** Run `make install`, `make check-frontend`, and `make check-mcp`. Start a disposable `postgres:17-alpine` container on host port 55432 with CI credentials/database, wait until `psql -c 'SELECT 1'` succeeds against the configured test database (avoids the image bootstrap race), run backend `alembic upgrade head`, then the full root `make check` with CI-equivalent `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, and `POSTGRES_PASSWORD`. Always remove the disposable container after testing.
- [x] **Step 4: Audit and commit.** Run `make help`, `make -n install`, `make -n check`, `git diff --check`, `git status --short`, and `git log --oneline --max-count=6`. Commit Compose cleanup and this plan with `chore: modernize developer foundations`.

## Task 6: Close audit-discovered safety gaps

**Files:** Modify `backend/app/main.py`, add `backend/tests/test_app_import.py`, and correct affected guidance.

- [x] **Step 1: Remove import-time schema DDL.** Delete `Base.metadata.create_all` from application import so Alembic remains the sole schema authority.
- [x] **Step 2: Protect the behavior.** Add a fresh-process regression test that patches `Base.metadata.create_all` before importing `app.main` and fails if import invokes it.
- [x] **Step 3: Reconcile onboarding.** Require the component-local backend `.env` with its four required settings, run Alembic before API startup, explain that backend tests need a dedicated database, and remove stale test examples.
- [x] **Step 4: Verify.** Run the import regression, backend static checks, both Compose config validations, and the full root check against a migrated disposable database.

## Task 7: Correct the full-gate gene normalization invariant

**Files:** Modify `backend/app/core/gene_normalizer.py`, `backend/tests/test_gene_normalization.py`, and `backend/tests/core/test_validators.py`.

- [x] **Step 1: Reproduce the invariant failure.** The full backend property suite found that an input such as `G:ENE` normalized to `GENE`, then to an empty string on a second pass.
- [x] **Step 2: Make cleaning idempotent.** Preserve literal `GENE` and `PROTEIN` tokens while excluding them as likely symbols, remove repeated tag prefixes safely, and consume only terminal `GENE`, `PROTEIN`, and `_HUMAN` suffix tokens.
- [x] **Step 3: Bound normalization work.** Use direct terminal-token consumption rather than repeated full-string regular-expression substitutions, protecting long suffix runs and long near-miss inputs from quadratic behavior.
- [x] **Step 4: Protect and verify.** Add explicit idempotence, repeated-suffix, and long near-miss regression tests; run the focused backend suite and the full migrated-database root check.
