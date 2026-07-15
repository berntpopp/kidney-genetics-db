# Developer Foundations Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repository reproducible and safe to develop with any major coding agent by centralizing instructions, adding deterministic root commands, aligning CI, and correcting onboarding documentation.

**Architecture:** `AGENTS.md` is the durable, tool-neutral authority; `CLAUDE.md` only imports it. The root Makefile orchestrates the independently locked backend, frontend, and MCP projects. CI invokes the same focused gates.

**Tech Stack:** Python 3.13 local/CI baseline with uv, Node >=22.18.0 with npm, Docker Compose v2, FastAPI, Vue/Vite, FastMCP, GitHub Actions, GNU Make.

---

## Task 1: Add shared cross-LLM guidance

**Files:** Create `AGENTS.md`; modify `CLAUDE.md`.

- [ ] **Step 1: Write the failing layout check.** Run `test -f AGENTS.md`; it must fail before implementation.
- [ ] **Step 2: Create the guide.** Add `AGENTS.md` with exact sections: Project Context; Repository Map; Prerequisites and Setup; Common Commands; Development Boundaries; Component Conventions; Testing and Verification; Multi-Agent and Handoff Workflow; Pull Request Expectations. It must document backend/frontend/MCP/scrapers/Compose/`.planning`, Python 3.13 local/CI, Node >=22.18.0, backend production Python 3.14, Docker Compose v2, component lockfiles, API-mediated pipelines, Alembic, existing core utilities, MCP contract generation, generated-data and secret rules, conventional commits, and agent handoffs. State that `scrapers/diagnostics` is excluded from root installation/checks until it declares dependencies and tests.
- [ ] **Step 3: Replace `CLAUDE.md` exactly.** Its five lines must be: heading `# Claude Code Instructions`; blank line; `Read and follow \`AGENTS.md\` for all repository guidance.`; blank line; `@AGENTS.md`.
- [ ] **Step 4: Verify.** Run `test -f AGENTS.md`; `test "$(wc -l < CLAUDE.md)" -eq 5`; `rg -n '^@AGENTS\\.md$' CLAUDE.md`; `! rg -n 'Current Status.*v0\\.2\\.0|There is no separate \`docs/\` directory' CLAUDE.md AGENTS.md`; and `git diff --check`. All must succeed.
- [ ] **Step 5: Commit.** Run `git add AGENTS.md CLAUDE.md` then `git commit -m "docs: add shared agent guidance"`.

## Task 2: Add deterministic root commands

**Files:** Modify `Makefile`.

- [ ] **Step 1: Write the failing behavior check.** Run `make -n lint | rg 'ruff check app/ --fix'`; it proves the existing validation target mutates source.
- [ ] **Step 2: Add locked bootstrap targets.** Add `install` depending on `install-backend install-frontend install-mcp`. The backend and MCP recipes are `uv sync --locked --group dev` in their directories; the frontend recipe is `npm ci` in `frontend/`. Include all in `.PHONY`; make `mcp-build` a compatibility alias for `install-mcp`.
- [ ] **Step 3: Add non-mutating checks.** `check` depends on `check-backend check-frontend check-mcp`. Backend check runs `uv lock --check`, `ruff check --no-fix app/`, `ruff format --check app/`, and `pytest tests/ -v`. Frontend check runs `npm run lint:check`, `npm run format:check`, `npm run build`, and `npm run test:run`. MCP check runs `uv lock --check`, `ruff check .`, `ruff format --check .`, `mypy src/`, `pytest`, then the read-only `make -C mcp contract-verify`.
- [ ] **Step 4: Make mutation explicit.** Change `lint` to checking only. Add `lint-fix` for backend `ruff check --fix` and frontend `npm run lint`; add `format` for backend/MCP `ruff format` and frontend `npm run format`; include MCP in `format-check`. Define `ci-backend`, `ci-frontend`, and `ci-mcp` as wrappers and make `ci` depend on all three. Preserve legacy test/service/database targets.
- [ ] **Step 5: Update help and verify target shape.** `make help` must list bootstrap, checks, explicit fixes, and the database requirement for backend checks. Run `make -n install`, `make -n check`, every focused check dry-run, `! make -n lint | rg -- '--fix'`, `make -n lint-fix | rg -- '--fix'`, and `make -n format-check | rg 'cd mcp && uv run ruff format --check \\.'`.
- [ ] **Step 6: Run database-free checks.** Run `make check-frontend` and `make check-mcp`; both must pass.
- [ ] **Step 7: Commit.** Run `git add Makefile` then `git commit -m "build: add deterministic development commands"`.

## Task 3: Align CI with local commands

**Files:** Modify `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `.github/workflows/lighthouse.yml`.

- [ ] **Step 1: Write the failing CI check.** Run `! rg -n 'mcp-ci|MCP CI' .github/workflows/ci.yml`; it succeeds because MCP is currently absent.
- [ ] **Step 2: Add MCP CI.** Add `mcp` to changes outputs and `dorny/paths-filter`, matching `mcp/**`, `Makefile`, and `.github/workflows/ci.yml`. Add `mcp-ci`, conditional on the filter, with `astral-sh/setup-uv@v7` caching `mcp/uv.lock`, `actions/setup-python@v6` at Python 3.13, locked MCP sync, then `make check-mcp` from root. Add MCP to `ci-summary` needs, Markdown table, and failure handling.
- [ ] **Step 3: Align dependency/runtime commands.** Change backend CI sync to `uv sync --locked --group dev`. Replace frontend `node-version: '22'` in CI, security, and Lighthouse with `node-version: '22.18.x'`; keep the compatible Node 26 Docker builder.
- [ ] **Step 4: Verify workflow content.** Parse every workflow through `yaml.safe_load` using `backend`'s uv environment; then search `.github/workflows` for `mcp-ci`, `mcp/**`, locked sync, and the 22.18.x Node range. Expect all assertions to pass.
- [ ] **Step 5: Commit.** Run `git add .github/workflows/ci.yml .github/workflows/security.yml .github/workflows/lighthouse.yml` then `git commit -m "ci: verify MCP and locked dependencies"`.

## Task 4: Refresh onboarding and component documentation

**Files:** Modify `README.md`, `backend/README.md`, `backend/TESTING.md`, `frontend/README.md`, `mcp/README.md`.

- [ ] **Step 1: Replace root setup guidance.** Document Git; Docker Compose v2; uv; Python 3.13 local/CI with backend production Python 3.14; Node >=22.18.0; and the sequence `make install`, optional `cp .env.example .env`, `make hybrid-up`, `make backend`, `make frontend`, optional `make worker`, optional `make mcp`. State that `make services-up` precedes backend checks, list check/CI/security commands, set static version/citation text to 0.5.1, and link `AGENTS.md`.
- [ ] **Step 2: Use one component install model.** Component READMEs use `make install-backend`, `make install-frontend`, and `make install-mcp`; local alternatives use locked uv sync or `npm ci`, never bare `npm install`, `uv sync --dev`, or bare `pytest`. Replace generic frontend documentation with project run/build/test/E2E guidance. Make backend testing recommend Docker PostgreSQL plus `make services-up` and `make check-backend`, not system Postgres build packages.
- [ ] **Step 3: Preserve an honest scraper boundary.** Root README and `AGENTS.md` must say diagnostics is a legacy utility without a dependency manifest, lockfile, or test gate and is therefore excluded from root install/check until a dedicated packaging modernization.
- [ ] **Step 4: Verify and commit.** Run `! rg -n 'Node\\.js 18\\+|Python 3\\.14\\+|uv sync --dev|npm install' README.md backend/README.md backend/TESTING.md frontend/README.md mcp/README.md AGENTS.md`; search README/AGENTS for all four new command families; verify README contains `0.5.1`; run `git diff --check`; then commit with `docs: document reproducible development setup`.

## Task 5: Remove obsolete Compose metadata and run complete verification

**Files:** Modify `docker-compose.yml`, `docker-compose.services.yml`.

- [ ] **Step 1: Remove only the obsolete `version: '3.8'` line from each Compose file.** Do not modify any service configuration.
- [ ] **Step 2: Validate Compose without warnings.** Run `docker compose -f docker-compose.yml config --quiet` and the services variant, each redirecting stderr to a temporary file; both files must be empty. Remove the temporary files.
- [ ] **Step 3: Run full checks.** Run `make install`, `make check-frontend`, and `make check-mcp`. Start a disposable `postgres:17-alpine` container on host port 55432 with CI credentials/database, wait for `pg_isready`, run backend `alembic upgrade head`, then `pytest tests/ -v --cov=app --cov-report=term-missing --timeout=300` with CI-equivalent `DATABASE_URL`, `TEST_DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, and `POSTGRES_PASSWORD`. Always remove the disposable container after testing.
- [ ] **Step 4: Audit and commit.** Run `make help`, `make -n install`, `make -n check`, `git diff --check`, `git status --short`, and `git log --oneline --max-count=6`. Commit Compose cleanup and this plan with `chore: modernize developer foundations`.
