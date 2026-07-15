# Developer Foundations Modernization — Design Spec

- **Date:** 2026-07-15
- **Status:** Approved for implementation
- **Scope:** Cross-LLM repository guidance, reproducible developer setup,
  root command ergonomics, CI coverage, and onboarding documentation.

## 1. Problem and evidence

Kidney-Genetics Database is a multi-component repository:

- `backend/`: FastAPI, PostgreSQL, Alembic, Redis/ARQ; `uv.lock` is committed.
- `frontend/`: Vue 3/Vite; `package-lock.json` is committed.
- `mcp/`: read-only FastMCP server; `uv.lock` is committed and its own strict
  `Makefile` already defines `check` and `contract-verify`.
- `scrapers/`: independent diagnostic and literature utilities.

The initial audit found the following developer-experience drift:

1. The repository has no `AGENTS.md`; its 372-line `CLAUDE.md` is the only
   agent guide and is stale (v0.2.0, no `docs/` claim, and outdated workflow
   statements).
2. There is no root deterministic installation command or unified check that
   includes the MCP server.
3. `make lint` silently modifies backend files, despite being described as a
   validation command.
4. Root documentation disagrees about requirements: the frontend requires
   Node >=22.18.0, while the README says Node 18+; backend CI is Python 3.13,
   while the production image is Python 3.14.
5. The main CI workflow does not test the MCP component. The two Compose files
   used for development emit warnings because their top-level `version` keys
   are obsolete.
6. The diagnostic scraper has tooling configuration only: it has neither a
   declared dependency set nor a lockfile. It cannot truthfully be included in
   a reproducible root bootstrap yet.

Comparison projects `../sysndd-manuscript` and `../vntyper-manuscript` use a
shared `AGENTS.md`, a five-line `CLAUDE.md` bridge, concise setup commands,
focused verification guidance, and explicit multi-agent handoff rules. Their
model is adopted here, with application-specific safety rules.

## 2. Research-informed decisions

- **One durable instruction source:** Codex treats `AGENTS.md` as the
  repository-level place for commands, conventions, constraints, and
  verification. Claude Code supports importing it from a minimal `CLAUDE.md`.
  GitHub Copilot agents also support nearest-ancestor `AGENTS.md` guidance.
- **Deterministic installs:** `uv sync --locked --group dev` must be used for
  Python components. It verifies that the committed lockfile matches metadata
  before creating the exact synced environment. `npm ci` must be used for the
  frontend: it requires a consistent lockfile, removes an existing
  `node_modules`, and never rewrites the lockfile.
- **Command intent must be explicit:** checks do not change tracked source;
  fix/format commands make source changes intentionally. Root aggregate
  commands are wrappers around the actual component commands CI runs.
- **Runtime policy:** Python 3.13 is the local and CI baseline because it is
  compatible with backend (`>=3.10`) and MCP (`>=3.11`) metadata and is already
  tested by CI. Backend production remains Python 3.14; this is documented as
  a deliberate deployment choice rather than misrepresented as the local
  requirement. Node >=22.18.0 is required by `frontend/package.json`; Actions
  use the matching `22.18.x` range. The frontend production image may use
  newer compatible Node 26.

Sources consulted: official Codex customization guidance, Claude Code memory
guidance, GitHub Copilot repository instruction documentation, uv lock/sync
documentation, npm `ci` documentation, and GitHub Actions Python/Node guidance.

## 3. Target developer interface

### 3.1 Repository guidance

Create a root `AGENTS.md` of approximately 150–200 focused lines. It will:

- describe the application and the ownership of the backend, frontend, MCP,
  Compose, scraper, and `.planning/` areas;
- give prerequisites, deterministic setup, normal development modes, and
  exact focused verification commands;
- protect sensitive and generated data, unrelated user changes, migrations,
  the data pipeline, and MCP's read-only security boundary;
- preserve project conventions: SQLAlchemy/Alembic, configuration/env
  boundaries, existing core utilities, API clients, strict MCP contract
  generation, conventional commits, and source-specific data provenance;
- define work handoff/parallel-edit rules and PR evidence expectations.

Replace root `CLAUDE.md` with a minimal bridge:

```markdown
# Claude Code Instructions

Read and follow `AGENTS.md` for all repository guidance.

@AGENTS.md
```

Do not create duplicate Copilot/Gemini-specific instruction files. This avoids
conflicting policies while `AGENTS.md` is the cross-agent authority.

### 3.2 Make targets

The root `Makefile` will expose the following non-destructive interface:

| Purpose | Root command | Contract |
| --- | --- | --- |
| Install all maintained components | `make install` | Runs the three component install targets. |
| Install backend | `make install-backend` | `uv sync --locked --group dev` in `backend/`. |
| Install frontend | `make install-frontend` | `npm ci` in `frontend/`. |
| Install MCP | `make install-mcp` | `uv sync --locked --group dev` in `mcp/`. |
| Check all maintained components | `make check` | Runs backend, frontend, then MCP checks; backend requires PostgreSQL. |
| Backend check | `make check-backend` | Lock check, Ruff lint/format check, then backend tests. |
| Frontend check | `make check-frontend` | ESLint, Prettier check, production build, and Vitest. |
| MCP check | `make check-mcp` | Lock check, Ruff lint/format check, strict mypy, pytest, and contract drift check. |
| Apply safe formatting/fixes | `make lint-fix` / `make format` | Explicitly mutating targets only. |
| Validate formatting | `make format-check` | Checks backend, frontend, and MCP without modifying files. |

Existing public targets remain as compatibility aliases where practical:
`make ci`, `make ci-backend`, `make ci-frontend`, `make mcp-build`, and
`make mcp-test`. `make lint` changes from auto-fixing to checking; `make
lint-fix` preserves the old explicit fix behavior.

The command help text will group bootstrap, quality, test, service, database,
MCP, and deployment workflows, and will call out database preconditions for
backend tests. The diagnostic scraper is excluded from root `install` and
`check` because it lacks dependency metadata; its limitation is made explicit.

### 3.3 CI alignment

Extend `.github/workflows/ci.yml` with:

- an `mcp` path filter and an `mcp-ci` job using Python 3.13, uv caching, locked
  sync, and the same `make check-mcp` command used locally;
- MCP result reporting and failure handling in `ci-summary`;
- locked Python dependency synchronization in backend CI;
- Node `22.18.x` in frontend CI, Lighthouse, and frontend security scans.

The codebase remains component-specific: backend integration testing continues
to use PostgreSQL in CI, whereas MCP and frontend checks remain database-free.
No CI path filter is added for the diagnostic scraper until it has reproducible
dependencies and tests.

### 3.4 Documentation and Compose cleanup

Refresh the root README as the onboarding entry point:

1. state the component-specific prerequisites and supported operating modes;
2. give tool-install links/commands, deterministic `make install`, environment
   setup, and development startup instructions;
3. present a concise command table, verification steps, and links to detailed
   component documentation and `AGENTS.md`.

Update `backend/README.md`, `backend/TESTING.md`, `frontend/README.md`, and
`mcp/README.md` so their install and verification instructions point to the
same locked commands and no longer state obsolete requirements. Remove only
the obsolete top-level Compose `version:` keys from `docker-compose.yml` and
`docker-compose.services.yml`; service behavior remains unchanged.

## 4. Non-goals and follow-up boundary

This change deliberately does not:

- upgrade application dependencies, refactor runtime business logic, migrate
  the database, or change deployment behavior;
- add a new framework or package manager;
- package the diagnostic scraper without first collecting its actual runtime
  dependencies and creating focused tests;
- add a separate Copilot/Gemini instructions file that duplicates `AGENTS.md`.

The next modernization specification should make the diagnostic scraper a
proper package (PEP 621 metadata, explicit dependencies, lockfile, tests, and
CI), then include it in root commands and agent guidance.

## 5. Verification requirements

Implementation is complete only when all of the following are evidenced:

1. `AGENTS.md` is the shared source; `CLAUDE.md` imports it and has no duplicate
   rules.
2. `make help`, `make -n install`, `make -n check`, and each focused target
   resolve to the documented commands without unexpected source modification.
3. Locked installs work for backend and MCP; `npm ci` works for frontend.
4. `make check-frontend` and `make check-mcp` pass; backend static checks and
   database-backed tests are run with the explicit CI-equivalent environment.
5. `docker compose -f docker-compose.yml config --quiet` and the services
   variant complete without obsolete-version warnings.
6. Workflow YAML is parsed and the CI path/job/summary graph includes MCP.
7. README/component instructions, Make help, and `AGENTS.md` agree on command
   names and requirements.
8. `git diff --check` and the full relevant check suite pass before handoff.
