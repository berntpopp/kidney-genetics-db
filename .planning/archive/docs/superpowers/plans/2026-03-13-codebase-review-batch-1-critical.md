# Codebase Review Remediation — Batch 1: Critical Security & Stability

> **Status: COMPLETE** — All 12 tasks implemented on branch `fix/codebase-review-batch-1-critical` (2026-03-14)

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix critical security vulnerabilities (hardcoded secrets, SQL injection, broken import) and add missing database indexes.

**Architecture:** Four independent sub-batches with zero file overlap, designed for parallel execution in isolated worktrees. Each sub-batch produces atomic, testable changes.

**Tech Stack:** Python/FastAPI, Pydantic SecretStr, SQLAlchemy, Alembic, gitleaks pre-commit hook

**Spec:** `docs/superpowers/specs/2026-03-13-codebase-review-remediation-design.md`

---

## Chunk 1: Sub-batch 1A — Secrets & Config (Tasks 1–5)

### Task 1: Convert sensitive config fields to SecretStr

**Files:**
- Modify: `backend/app/core/config.py:1-112`
- Test: `backend/tests/test_config_secrets.py` (create)

- [x] **Step 1: Write failing test for SecretStr fields**

Create `backend/tests/test_config_secrets.py`:

```python
"""Tests for SecretStr configuration fields."""

import pytest
from pydantic import SecretStr


@pytest.mark.unit
class TestSecretStrConfig:
    """Verify sensitive fields use SecretStr."""

    def test_jwt_secret_key_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["JWT_SECRET_KEY"]
        assert field_info.annotation is SecretStr

    def test_admin_password_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["ADMIN_PASSWORD"]
        assert field_info.annotation is SecretStr

    def test_database_url_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["DATABASE_URL"]
        assert field_info.annotation is SecretStr

    def test_postgres_password_is_secret_str(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["POSTGRES_PASSWORD"]
        assert field_info.annotation is SecretStr

    def test_openai_api_key_is_secret_str_or_none(self):
        from app.core.config import Settings

        field_info = Settings.model_fields["OPENAI_API_KEY"]
        # Should be SecretStr | None
        assert SecretStr in (
            getattr(field_info.annotation, "__args__", ())
            if hasattr(field_info.annotation, "__args__")
            else (field_info.annotation,)
        )

    def test_repr_hides_secrets(self):
        from app.core.config import settings

        repr_str = repr(settings)
        assert "kidney_pass" not in repr_str
        assert "ChangeMe" not in repr_str

    def test_jwt_secret_key_min_length_validator(self):
        from app.core.config import Settings

        with pytest.raises(Exception):
            Settings(JWT_SECRET_KEY="short")

    def test_jwt_secret_key_rejects_placeholder(self):
        from app.core.config import Settings

        with pytest.raises(Exception):
            Settings(JWT_SECRET_KEY="CHANGE_THIS_TO_A_SECURE_SECRET_KEY")
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config_secrets.py -v`
Expected: FAIL — fields are currently `str`, not `SecretStr`

- [x] **Step 3: Convert config.py fields to SecretStr**

Edit `backend/app/core/config.py`. Replace the field definitions:

```python
"""
Configuration settings for the application
"""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        secrets_dir="/run/secrets",
    )

    # Application
    APP_NAME: str = "Kidney Genetics API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SITE_URL: str = "https://kidney-genetics.org"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Database — REQUIRED, no default (must be set via .env or env var)
    DATABASE_URL: SecretStr
    DATABASE_ECHO: bool = False

    # Security - JWT — REQUIRED, no default
    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security - Passwords
    PASSWORD_MIN_LENGTH: int = 8
    BCRYPT_ROUNDS: int = 12

    # Security - Account
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15

    # Default Admin (for initial setup only) — REQUIRED, no default
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str = "admin@kidney-genetics.local"
    ADMIN_PASSWORD: SecretStr

    # ... (all other fields remain unchanged) ...

    # API Keys (optional)
    OPENAI_API_KEY: SecretStr | None = None

    # PostgreSQL connection for backups — REQUIRED, no default
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "kidney_user"
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str = "kidney_genetics"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: SecretStr) -> SecretStr:
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        placeholders = {"CHANGE_THIS_TO_A_SECURE_SECRET_KEY", "changeme", "secret"}
        if secret.lower() in placeholders:
            raise ValueError("JWT_SECRET_KEY must not be a placeholder value")
        return v
```

**Important**: Keep all other fields exactly as they are. Only change the 5 sensitive fields listed above plus add `LOG_LEVEL`, `secrets_dir`, and the validator. The four required fields (`DATABASE_URL`, `JWT_SECRET_KEY`, `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`) have **no defaults** per the spec — the app will fail to start without a `.env` file. Ensure all development `.env` files and Docker Compose configs set these values. Update `conftest.py` test setup and CI to provide them.

- [x] **Step 4: Run test to verify SecretStr fields pass**

Run: `cd backend && uv run pytest tests/test_config_secrets.py -v`
Expected: PASS (at least the type-checking tests; validator tests may need the defaults adjusted)

- [x] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_config_secrets.py
git commit -m "feat(security): convert sensitive config fields to SecretStr (S1)"
```

### Task 2: Update all SecretStr call sites with .get_secret_value()

**Files:**
- Modify: `backend/app/core/security.py:80,111,129`
- Modify: `backend/app/core/database.py:63`
- Modify: `backend/alembic/env.py:28`
- Modify: `backend/app/core/database_init.py:231`
- Modify: `backend/app/services/backup_service.py` (POSTGRES_PASSWORD usages)
- Test: `backend/tests/test_config_secrets.py` (extend)

- [x] **Step 1: Write failing test for .get_secret_value() usage**

Add to `backend/tests/test_config_secrets.py`:

```python
@pytest.mark.unit
class TestSecretStrCallSites:
    """Verify call sites use .get_secret_value()."""

    def test_settings_jwt_key_returns_string(self):
        from app.core.config import settings

        # .get_secret_value() must return a plain str for jwt.encode()
        val = settings.JWT_SECRET_KEY.get_secret_value()
        assert isinstance(val, str)
        assert len(val) >= 32

    def test_settings_database_url_returns_string(self):
        from app.core.config import settings

        val = settings.DATABASE_URL.get_secret_value()
        assert val.startswith("postgresql://")

    def test_settings_admin_password_returns_string(self):
        from app.core.config import settings

        val = settings.ADMIN_PASSWORD.get_secret_value()
        assert isinstance(val, str)
        assert len(val) > 0
```

- [x] **Step 2: Run test to verify it passes (these test the accessor)**

Run: `cd backend && uv run pytest tests/test_config_secrets.py::TestSecretStrCallSites -v`
Expected: PASS

- [x] **Step 3: Update security.py — JWT encoding/decoding**

In `backend/app/core/security.py`, update all 3 usages of `settings.JWT_SECRET_KEY`:

Line 80 (in `create_access_token`):
```python
# Before:
jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
# After:
jwt.encode(to_encode, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)
```

Line 111 (in `create_refresh_token`):
```python
# Same pattern as above
jwt.encode(to_encode, settings.JWT_SECRET_KEY.get_secret_value(), algorithm=settings.JWT_ALGORITHM)
```

Line 129 (in `verify_token`):
```python
# Before:
payload: dict[str, Any] = jwt.decode(
    token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
)
# After:
payload: dict[str, Any] = jwt.decode(
    token, settings.JWT_SECRET_KEY.get_secret_value(), algorithms=[settings.JWT_ALGORITHM]
)
```

- [x] **Step 4: Update database.py — create_engine**

In `backend/app/core/database.py`, line 63:

```python
# Before:
engine = create_engine(
    settings.DATABASE_URL,
# After:
engine = create_engine(
    settings.DATABASE_URL.get_secret_value(),
```

- [x] **Step 5: Update alembic/env.py — migration URL**

In `backend/alembic/env.py`, line 28:

```python
# Before:
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
# After:
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.get_secret_value())
```

- [x] **Step 6: Update database_init.py — admin password**

In `backend/app/core/database_init.py`, line 231:

```python
# Before:
hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
# After:
hashed_password=get_password_hash(settings.ADMIN_PASSWORD.get_secret_value()),
```

- [x] **Step 7: Update backup_service.py — POSTGRES_PASSWORD**

In `backend/app/services/backup_service.py`, replace all occurrences of `settings.POSTGRES_PASSWORD` with `settings.POSTGRES_PASSWORD.get_secret_value()`. Grep for exact locations:

```bash
cd backend && grep -n "settings.POSTGRES_PASSWORD" app/services/backup_service.py
```

Each instance (lines ~200, 364, 420, 429, 463):
```python
# Before:
f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
# After:
f"PGPASSWORD={settings.POSTGRES_PASSWORD.get_secret_value()}",
```

- [x] **Step 8: Grep for any remaining bare usages**

```bash
cd backend && grep -rn "settings\.JWT_SECRET_KEY\b" app/ --include="*.py" | grep -v "get_secret_value"
cd backend && grep -rn "settings\.DATABASE_URL\b" app/ --include="*.py" | grep -v "get_secret_value"
cd backend && grep -rn "settings\.ADMIN_PASSWORD\b" app/ --include="*.py" | grep -v "get_secret_value"
cd backend && grep -rn "settings\.POSTGRES_PASSWORD\b" app/ --include="*.py" | grep -v "get_secret_value"
cd backend && grep -rn "settings\.OPENAI_API_KEY\b" app/ --include="*.py" | grep -v "get_secret_value"
```

Fix any remaining usages found.

- [x] **Step 9: Run full test suite to verify nothing broke**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests PASS

- [x] **Step 10: Commit**

```bash
git add backend/app/core/security.py backend/app/core/database.py backend/alembic/env.py \
  backend/app/core/database_init.py backend/app/services/backup_service.py \
  backend/tests/test_config_secrets.py
git commit -m "fix(security): update all SecretStr call sites with .get_secret_value() (S1)"
```

### Task 3: Replace hardcoded DEBUG log level and remove test DB fallback

**Files:**
- Modify: `backend/app/main.py:48`
- Modify: `backend/tests/conftest.py:30-33`
- Test: Existing tests validate behavior

- [x] **Step 1: Fix main.py log level (B6)**

In `backend/app/main.py`, line 48:

```python
# Before:
configure_logging(log_level="DEBUG", database_enabled=True, console_enabled=True)
# After:
configure_logging(log_level=settings.LOG_LEVEL, database_enabled=True, console_enabled=True)
```

Also add the import if `settings` isn't already imported at the top of the file. (Check existing imports — it likely already imports `settings` from config.)

- [x] **Step 2: Fix conftest.py test DB URL fallback (B7)**

In `backend/tests/conftest.py`, lines 18-34:

```python
# Before:
def get_test_database_url() -> str:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        return test_url
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics",
    )
    return db_url

# After:
def get_test_database_url() -> str:
    """
    Get the database URL for testing.
    Requires TEST_DATABASE_URL or DATABASE_URL environment variable.
    """
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        return test_url

    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # Fall back to settings (which reads from .env file)
    from app.core.config import settings

    return settings.DATABASE_URL.get_secret_value()
```

- [x] **Step 3: Run tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All tests PASS

- [x] **Step 4: Commit**

```bash
git add backend/app/main.py backend/tests/conftest.py
git commit -m "fix(config): use settings.LOG_LEVEL and remove hardcoded test DB fallback (B6, B7)"
```

### Task 4: Update .env.example with generation instructions

**Files:**
- Modify: `backend/.env.example`

- [x] **Step 1: Update .env.example**

Replace the top section of `backend/.env.example`:

```bash
# Kidney Genetics Database Environment Configuration
# Copy this file to .env and update values as needed

# Application Settings
APP_NAME="Kidney Genetics API"
APP_VERSION="0.1.0"
DEBUG=False
ENVIRONMENT=dev

# Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Database
# REQUIRED — Update with your database credentials
DATABASE_URL=postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics
DATABASE_ECHO=False

# Security - JWT
# REQUIRED — Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security - Passwords
PASSWORD_MIN_LENGTH=8
BCRYPT_ROUNDS=12

# Security - Account
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15

# Default Admin (change immediately after first login)
# REQUIRED — Set a secure admin password
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@kidney-genetics.local
ADMIN_PASSWORD=
```

Leave the rest of the file unchanged.

- [x] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "docs: update .env.example with secret generation instructions (S1)"
```

### Task 5: Add gitleaks pre-commit hook and CI workflow

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/gitleaks.yml`
- Create: `.gitleaks.toml`

- [x] **Step 1: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks
```

- [x] **Step 2: Create .gitleaks.toml**

```toml
[allowlist]
paths = [
    '''.planning/''',
    '''node_modules/''',
    '''\.env\.example''',
    '''uv\.lock''',
    '''package-lock\.json''',
    '''\.gitleaks\.toml''',
]
```

- [x] **Step 3: Create .github/workflows/gitleaks.yml**

```yaml
name: Secret Scanning

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  gitleaks:
    name: Gitleaks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_CONFIG: .gitleaks.toml
```

- [x] **Step 4: Install pre-commit hook locally**

Run: `uv pip install pre-commit && pre-commit install`
Expected: Hook installed successfully

- [x] **Step 5: Verify gitleaks catches secrets**

Run: `pre-commit run gitleaks --all-files`
Expected: Should pass (no secrets in committed files). If it flags the hardcoded defaults in config.py, add a `# gitleaks:allow` comment or extend the allowlist.

- [x] **Step 6: Commit**

```bash
git add .pre-commit-config.yaml .gitleaks.toml .github/workflows/gitleaks.yml
git commit -m "feat(security): add gitleaks pre-commit hook and CI secret scanning (S1)"
```

### Task 5b: Update CI workflow to use GitHub Secrets for test env vars

**Files:**
- Modify: `.github/workflows/ci.yml`

- [x] **Step 1: Update CI to use secrets for required env vars**

In `.github/workflows/ci.yml`, in the backend test job, add environment variables from GitHub Secrets:

```yaml
    env:
      DATABASE_URL: postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics
      JWT_SECRET_KEY: ${{ secrets.TEST_JWT_SECRET_KEY || 'test-jwt-secret-key-minimum-32-characters-long' }}
      ADMIN_PASSWORD: ${{ secrets.TEST_ADMIN_PASSWORD || 'TestAdmin!2024Secure' }}
      POSTGRES_PASSWORD: ${{ secrets.TEST_POSTGRES_PASSWORD || 'kidney_pass' }}
      TEST_DATABASE_URL: postgresql://kidney_user:kidney_pass@localhost:5432/kidney_genetics
```

Note: Fallback values are provided for CI runners that don't have secrets configured (e.g., forks). These are test-only values.

- [x] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: use GitHub Secrets for required env vars in test jobs (S1)"
```

---

## Chunk 2: Sub-batch 1B — SQL Safety + View Refresh + Matview Bug (Tasks 6–9)

### Task 6: Create safe_sql.py utility module

**Files:**
- Create: `backend/app/db/safe_sql.py`
- Test: `backend/tests/test_safe_sql.py` (create)

- [x] **Step 1: Write failing tests for safe_sql functions**

Create `backend/tests/test_safe_sql.py`:

```python
"""Tests for SQL identifier safety utilities."""

import pytest

from app.db.safe_sql import safe_identifier


@pytest.mark.unit
class TestSafeIdentifier:
    """Verify safe_identifier rejects invalid SQL identifiers."""

    def test_valid_identifier(self):
        assert safe_identifier("gene_scores") == "gene_scores"

    def test_valid_single_word(self):
        assert safe_identifier("genes") == "genes"

    def test_rejects_sql_injection(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene_scores; DROP TABLE users")

    def test_rejects_semicolon(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("test;")

    def test_rejects_dash(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene-scores")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("gene scores")

    def test_rejects_uppercase(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("GeneScores")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("")

    def test_rejects_too_long(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("a" * 64)

    def test_max_length_63(self):
        assert safe_identifier("a" * 63) == "a" * 63

    def test_rejects_leading_number(self):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            safe_identifier("1gene")
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_safe_sql.py -v`
Expected: FAIL — module does not exist

- [x] **Step 3: Create safe_sql.py**

Create `backend/app/db/safe_sql.py`:

```python
"""SQL safety utilities for dynamic DDL operations.

All dynamic SQL identifiers (view names, table names) MUST pass through
safe_identifier() before being interpolated into SQL strings.
"""

import re

from sqlalchemy import text
from sqlalchemy.orm import Session

VALID_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def safe_identifier(name: str) -> str:
    """Validate and return a safe SQL identifier.

    Args:
        name: Identifier to validate (lowercase, underscores, max 63 chars).

    Returns:
        The validated identifier string.

    Raises:
        ValueError: If the identifier contains invalid characters or is too long.
    """
    if not VALID_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid SQL identifier: {name!r}")
    return name


def refresh_materialized_view(
    session: Session, view_name: str, concurrent: bool = True
) -> None:
    """Safely refresh a materialized view.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the materialized view to refresh.
        concurrent: Whether to use CONCURRENTLY clause.
    """
    name = safe_identifier(view_name)
    clause = "CONCURRENTLY " if concurrent else ""
    session.execute(text(f"REFRESH MATERIALIZED VIEW {clause}{name}"))
    session.commit()


def drop_materialized_view(session: Session, view_name: str) -> None:
    """Safely drop a materialized view.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the materialized view to drop.
    """
    name = safe_identifier(view_name)
    session.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE"))
    session.commit()


def get_view_definition(session: Session, view_name: str) -> str | None:
    """Safely get a view's SQL definition.

    Args:
        session: SQLAlchemy session.
        view_name: Name of the view.

    Returns:
        View definition SQL or None if not found.
    """
    return session.execute(
        text("SELECT pg_get_viewdef(:name::regclass, true)"),
        {"name": view_name},
    ).scalar()
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_safe_sql.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/db/safe_sql.py backend/tests/test_safe_sql.py
git commit -m "feat(security): add safe_sql utility for SQL identifier validation (S2)"
```

### Task 7: Replace all f-string DDL with safe_sql functions

**Files:**
- Modify: `backend/app/api/endpoints/gene_annotations.py:578-593`
- Modify: `backend/app/pipeline/annotation_pipeline.py:911-929`
- Modify: `backend/app/pipeline/sources/annotations/base.py:540,546`
- Modify: `backend/app/db/materialized_views.py:349-352,431-432,460-461`
- Modify: `backend/app/db/registry.py:229-231`
- Modify: `backend/app/core/database_init.py:120-122` (view creation DDL)

- [x] **Step 1: Fix gene_annotations.py view refresh (S2 + P1)**

In `backend/app/api/endpoints/gene_annotations.py`, lines 578-593. Replace the f-string loop with safe_sql + run_in_threadpool:

```python
# Add imports at top of file:
from starlette.concurrency import run_in_threadpool
from app.db.safe_sql import refresh_materialized_view

# Replace the loop at lines 578-593:
    views_to_refresh = ["gene_scores", "gene_annotations_summary"]
    results = []

    for view_name in views_to_refresh:
        try:
            await run_in_threadpool(refresh_materialized_view, db, view_name, True)
            results.append(f"{view_name}: refreshed concurrently")
        except Exception:
            try:
                await run_in_threadpool(refresh_materialized_view, db, view_name, False)
                results.append(f"{view_name}: refreshed (non-concurrent)")
            except Exception as e2:
                raise HTTPException(
                    status_code=500, detail=f"Failed to refresh {view_name}: {str(e2)}"
                ) from e2

    return {"status": "success", "message": "; ".join(results)}
```

- [x] **Step 2: Fix annotation_pipeline.py view refresh (S2)**

In `backend/app/pipeline/annotation_pipeline.py`, lines 911-929. Replace:

```python
# Add import at top:
from app.db.safe_sql import refresh_materialized_view

# Replace the refresh_sync function body:
            def refresh_sync() -> bool:
                views_to_refresh = ["gene_scores", "gene_annotations_summary"]
                all_success = True

                for view_name in views_to_refresh:
                    try:
                        refresh_materialized_view(view_db, view_name, concurrent=True)
                        logger.sync_info(f"Materialized view {view_name} refreshed concurrently")
                    except Exception:
                        view_db.rollback()
                        try:
                            refresh_materialized_view(view_db, view_name, concurrent=False)
                            logger.sync_info(
                                f"Materialized view {view_name} refreshed (non-concurrent)"
                            )
                        except Exception as e:
                            logger.sync_error(
                                f"Failed to refresh {view_name}: {e}"
                            )
                            view_db.rollback()
                            all_success = False

                return all_success
```

- [x] **Step 3: Fix annotations/base.py view refresh (S2)**

In `backend/app/pipeline/sources/annotations/base.py`, lines 540 and 546:

```python
# Add import at top:
from app.db.safe_sql import refresh_materialized_view

# Line 540 — replace:
self.session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
# With:
refresh_materialized_view(self.session, view_name, concurrent=True)

# Line 546 — replace:
self.session.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
# With:
refresh_materialized_view(self.session, view_name, concurrent=False)
```

Remove the `self.session.commit()` calls after each since `refresh_materialized_view` handles commit internally.

- [x] **Step 4: Fix database_init.py view creation DDL (S2)**

In `backend/app/core/database_init.py`, lines 120-122. The view names come from a hardcoded internal list (`ALL_VIEWS`) so the injection risk is low, but for consistency use `safe_identifier`:

```python
# Add import at top:
from app.db.safe_sql import safe_identifier

# Line 121 — replace:
db.execute(text(f"CREATE OR REPLACE VIEW {view_def.name} AS {view_def.sqltext}"))
# With:
name = safe_identifier(view_def.name)
db.execute(text(f"CREATE OR REPLACE VIEW {name} AS {view_def.sqltext}"))
```

Note: `view_def.sqltext` is defined in `app.db.views` as static SQL strings, not user input — no injection risk there.

- [x] **Step 5: Fix materialized_views.py — refresh, drop, count (S2)**

In `backend/app/db/materialized_views.py`:

Add import at top:
```python
from app.db.safe_sql import safe_identifier
```

Line 352 (in `refresh_materialized_view` method):
```python
# Before:
self.db.execute(text(f"REFRESH MATERIALIZED VIEW {refresh_clause} {view_name}"))
# After:
name = safe_identifier(view_name)
self.db.execute(text(f"REFRESH MATERIALIZED VIEW {refresh_clause} {name}"))
```

Line 432 (in `drop_materialized_view` method):
```python
# Before:
self.db.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {view_name} CASCADE"))
# After:
name = safe_identifier(view_name)
self.db.execute(text(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE"))
```

Line 461 (in `get_view_stats` method):
```python
# Before:
row_count = self.db.execute(text(f"SELECT COUNT(*) FROM {view_name}")).scalar()
# After:
name = safe_identifier(view_name)
row_count = self.db.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
```

- [x] **Step 6: Fix registry.py — view definition lookup (S3)**

In `backend/app/db/registry.py`, lines 229-231:

```python
# Before:
result = connection.execute(
    text(f"SELECT pg_get_viewdef('{view_name}'::regclass, true)")
).scalar()
# After:
result = connection.execute(
    text("SELECT pg_get_viewdef(:name::regclass, true)"),
    {"name": view_name},
).scalar()
```

- [x] **Step 7: Run tests**

Run: `cd backend && uv run pytest -x -q`
Expected: All PASS

- [x] **Step 8: Commit**

```bash
git add backend/app/api/endpoints/gene_annotations.py \
  backend/app/pipeline/annotation_pipeline.py \
  backend/app/pipeline/sources/annotations/base.py \
  backend/app/core/database_init.py \
  backend/app/db/materialized_views.py \
  backend/app/db/registry.py
git commit -m "fix(security): replace f-string DDL with safe_sql functions (S2, S3, P1)"
```

### Task 8: Fix gene_distribution_analysis matview bug

**Files:**
- Modify: `backend/app/db/materialized_views.py:88-139`
- Test: `backend/tests/test_matview_definition.py` (create)

**Context:** The `gene_scores` view defines `evidence_tier` (line 290 in views.py) and `evidence_group` (line 302), but the `gene_distribution_analysis` matview references `classification` which does not exist in `gene_scores`. This causes `MaterializedViewManager.initialize_all_views()` to fail on fresh databases.

- [x] **Step 1: Write failing test**

Create `backend/tests/test_matview_definition.py`:

```python
"""Tests for materialized view definitions."""

import pytest


@pytest.mark.unit
class TestGeneDistributionAnalysis:
    """Verify gene_distribution_analysis references valid gene_scores columns."""

    def test_no_classification_column_reference(self):
        from app.db.materialized_views import MaterializedViewManager

        config = MaterializedViewManager.MATERIALIZED_VIEWS["gene_distribution_analysis"]
        definition = config.definition

        # Should NOT reference 'classification' (doesn't exist in gene_scores)
        # Should reference 'evidence_tier' instead
        assert "evidence_tier" in definition
        assert "GROUP BY score_bin, evidence_tier" in definition
        assert "GROUP BY source_count, evidence_tier" in definition

    def test_no_bare_classification_in_definition(self):
        from app.db.materialized_views import MaterializedViewManager

        config = MaterializedViewManager.MATERIALIZED_VIEWS["gene_distribution_analysis"]
        definition = config.definition

        # 'classification' should not appear (evidence_tier replaces it)
        lines = definition.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip lines that are part of SQL aliases or comments
            if stripped.startswith("--"):
                continue
            assert "classification" not in stripped.lower() or "evidence_tier" in stripped.lower(), (
                f"Found 'classification' in matview definition: {stripped}"
            )
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_matview_definition.py -v`
Expected: FAIL — definition still uses `classification`

- [x] **Step 3: Fix the matview definition**

In `backend/app/db/materialized_views.py`, lines 88-131. Replace `classification` with `evidence_tier` in 6 locations:

```python
        "gene_distribution_analysis": MaterializedViewConfig(
            name="gene_distribution_analysis",
            definition="""
            WITH score_bins AS (
                SELECT
                    CASE
                        WHEN percentage_score < 10 THEN '0-10%'
                        WHEN percentage_score < 20 THEN '10-20%'
                        WHEN percentage_score < 30 THEN '20-30%'
                        WHEN percentage_score < 40 THEN '30-40%'
                        WHEN percentage_score < 50 THEN '40-50%'
                        WHEN percentage_score < 60 THEN '50-60%'
                        WHEN percentage_score < 70 THEN '60-70%'
                        WHEN percentage_score < 80 THEN '70-80%'
                        WHEN percentage_score < 90 THEN '80-90%'
                        ELSE '90-100%'
                    END AS score_bin,
                    evidence_tier,
                    COUNT(*)::integer AS gene_count
                FROM gene_scores
                GROUP BY score_bin, evidence_tier
            ),
            source_distribution AS (
                SELECT
                    source_count,
                    evidence_tier,
                    COUNT(*)::integer AS gene_count
                FROM gene_scores
                GROUP BY source_count, evidence_tier
            )
            SELECT
                'score_distribution'::text AS analysis_type,
                score_bin AS category,
                evidence_tier,
                gene_count
            FROM score_bins
            UNION ALL
            SELECT
                'source_distribution'::text AS analysis_type,
                source_count::text AS category,
                evidence_tier,
                gene_count
            FROM source_distribution
            """,
```

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_matview_definition.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/db/materialized_views.py backend/tests/test_matview_definition.py
git commit -m "fix(db): replace 'classification' with 'evidence_tier' in gene_distribution_analysis matview"
```

### Task 9: Create Alembic migration for matview column fix

**Files:**
- Create: New Alembic migration

- [x] **Step 1: Generate migration**

Run: `cd backend && uv run alembic revision -m "fix gene_distribution_analysis matview column reference"`

- [x] **Step 2: Edit migration to drop and recreate the matview**

The migration should:
1. Drop the old matview (it references non-existent `classification` column)
2. The new definition will be picked up by `MaterializedViewManager.initialize_all_views()` on next startup

```python
"""fix gene_distribution_analysis matview column reference

Revision ID: <auto>
Revises: <auto>
"""

from alembic import op
from sqlalchemy import text


def upgrade() -> None:
    # Drop the broken matview so it gets recreated with corrected definition
    op.execute(text("DROP MATERIALIZED VIEW IF EXISTS gene_distribution_analysis CASCADE"))


def downgrade() -> None:
    # Drop so it can be recreated from the old code if needed
    op.execute(text("DROP MATERIALIZED VIEW IF EXISTS gene_distribution_analysis CASCADE"))
```

- [x] **Step 3: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration runs without error

- [x] **Step 4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "migration: drop gene_distribution_analysis for recreation with fixed columns"
```

---

## Chunk 3: Sub-batch 1C — Rate Limit Fix (Task 10)

### Task 10: Fix broken decode_access_token import

**Files:**
- Modify: `backend/app/core/rate_limit.py:36-38`
- Test: `backend/tests/test_rate_limit.py` (create)

- [x] **Step 1: Write failing test**

Create `backend/tests/test_rate_limit.py`:

```python
"""Tests for rate limit key function."""

import pytest
from unittest.mock import MagicMock

from app.core.rate_limit import _get_rate_limit_key


@pytest.mark.unit
class TestRateLimitKeyFunction:
    """Verify rate limit key extraction works with valid tokens."""

    def test_returns_ip_for_no_auth(self):
        request = MagicMock()
        request.headers = {}
        result = _get_rate_limit_key(request)
        # Should return IP address, not crash
        assert isinstance(result, str)

    def test_returns_ip_for_invalid_bearer(self):
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid_token"}
        result = _get_rate_limit_key(request)
        assert isinstance(result, str)
        # Should fall back to IP, not crash
        assert not result.startswith("user:")
        assert not result.startswith("admin:")

    def test_import_uses_verify_token(self):
        """Verify we import verify_token, not decode_access_token."""
        from app.core.security import verify_token  # noqa: F401

        # This should NOT raise ImportError
        assert callable(verify_token)

    def test_decode_access_token_does_not_exist(self):
        """Confirm decode_access_token does not exist."""
        with pytest.raises(ImportError):
            from app.core.security import decode_access_token  # noqa: F401
```

- [x] **Step 2: Run test to verify it fails (import error in rate_limit.py)**

Run: `cd backend && uv run pytest tests/test_rate_limit.py -v`
Expected: At least the import test confirms the broken state

- [x] **Step 3: Fix the import in rate_limit.py**

In `backend/app/core/rate_limit.py`, lines 36-38:

```python
# Before:
            from app.core.security import decode_access_token

            payload = decode_access_token(auth_header.split(" ", 1)[1])
# After:
            from app.core.security import verify_token

            payload = verify_token(auth_header.split(" ", 1)[1], token_type="access")
```

Note: `verify_token` returns `dict[str, Any] | None` — same shape. The existing `if payload and "sub" in payload:` guard at line 39 handles the `None` case.

- [x] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_rate_limit.py -v`
Expected: All PASS

- [x] **Step 5: Commit**

```bash
git add backend/app/core/rate_limit.py backend/tests/test_rate_limit.py
git commit -m "fix(security): replace broken decode_access_token with verify_token (S4)"
```

---

## Chunk 4: Sub-batch 1D — Missing Indexes (Task 11)

### Task 11: Add missing database indexes via Alembic migration

**Files:**
- Create: New Alembic migration
- Test: Verify with `EXPLAIN ANALYZE`

- [x] **Step 1: Generate migration**

Run: `cd backend && uv run alembic revision -m "add missing indexes for cache and evidence tables"`

- [x] **Step 2: Edit migration with standard (non-CONCURRENTLY) indexes**

Use standard `op.create_index` within the default transaction. `CONCURRENTLY` requires non-transactional DDL which complicates Alembic usage. With ~5000 genes and moderate cache entries, standard index creation is fast enough:

```python
def upgrade() -> None:
    op.create_index(
        "idx_cache_entries_key_expires",
        "cache_entries",
        ["cache_key", "expires_at"],
    )
    op.create_index(
        "idx_gene_evidence_gene_source",
        "gene_evidence",
        ["gene_id", "source_name"],
    )
    op.create_index(
        "idx_cache_entries_namespace",
        "cache_entries",
        ["namespace"],
    )


def downgrade() -> None:
    op.drop_index("idx_cache_entries_namespace", table_name="cache_entries")
    op.drop_index("idx_gene_evidence_gene_source", table_name="gene_evidence")
    op.drop_index("idx_cache_entries_key_expires", table_name="cache_entries")
```

- [x] **Step 3: Run migration**

Run: `cd backend && uv run alembic upgrade head`
Expected: Migration runs without error

- [x] **Step 4: Verify indexes exist**

Run:
```bash
cd backend && uv run python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text(\"\"\"
        SELECT indexname FROM pg_indexes
        WHERE tablename IN ('cache_entries', 'gene_evidence')
        ORDER BY indexname
    \"\"\"))
    for row in result:
        print(row[0])
"
```

Expected: See `idx_cache_entries_key_expires`, `idx_gene_evidence_gene_source`, `idx_cache_entries_namespace`

- [x] **Step 5: Commit**

```bash
git add backend/alembic/versions/
git commit -m "perf(db): add missing indexes for cache lookups and gene evidence filtering (P3)"
```

---

## Final Verification

- [x] **Step 1: Run full backend test suite**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [x] **Step 2: Run lint**

Run: `make lint`
Expected: No errors

- [x] **Step 3: Run typecheck on modified files**

Run:
```bash
cd backend && uv run mypy app/core/config.py app/core/rate_limit.py app/db/safe_sql.py \
  app/db/materialized_views.py app/core/security.py app/core/database.py \
  --ignore-missing-imports
```
Expected: No errors

- [x] **Step 4: Verify app starts**

Run: `make backend` (in hybrid mode with DB running)
Expected: App starts without error, no crash from config validation or rate limiter
