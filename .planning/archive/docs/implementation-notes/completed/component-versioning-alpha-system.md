# Component Versioning System for Alpha Phase - Implementation Plan

**Issue:** [#25 - Add version tracking for database, API, and frontend](https://github.com/berntpopp/kidney-genetics-db/issues/25)

**Status:** ✅ Planning Complete - Ready for Implementation
**Priority:** High
**Complexity:** Medium
**Estimated Time:** 12 hours
**Created:** 2025-01-10
**Planning Completed:** 2025-01-10

---

## 📋 Executive Summary

### Problem Statement

Version tracking is currently **inconsistent and incomplete**:
- **Backend:** v0.1.0 (in pyproject.toml)
- **Frontend:** v0.0.0 (in package.json)
- **Database:** No version tracking at all
- **No visibility:** Users/admins can't see what versions are running
- **No automation:** Manual version bumping prone to errors

**User Impact:**
- Cannot identify which version is deployed in any environment
- Cannot track changes between deployments
- Cannot debug "works in dev but not in prod" issues
- Cannot communicate feature availability to users

### Solution Overview

Implement **independent semantic versioning** for each component with:
- **Alpha versioning scheme:** All components stay 0.MINOR.PATCH until 1.0.0 release
- **Independent versioning:** Backend, frontend, and database evolve independently
- **Commit-based automation:** Versions auto-increment based on conventional commits
- **Simple visibility:** API endpoint + UI footer show all versions
- **Make integration:** `make version` and `make bump-*` commands

### Design Principles

**1. KISS (Keep It Simple)**
- Start with manual version bumping via Make commands
- No complex CI/CD initially (can add later)
- Simple API endpoint, simple UI footer
- No version compatibility matrices (just display)

**2. Alpha Forever (Until Decision)**
- **All components stay 0.x.x** until explicit decision to go 1.0.0
- 0.MINOR.PATCH semantic versioning within alpha
- No automatic graduation to 1.0.0

**3. Independent Component Versioning**
- Backend can be 0.3.5 while Frontend is 0.8.2
- Database schema version tracks independently
- No forced synchronization

**4. Conventional Commits Integration**
- Commits drive version increments
- `feat:` in backend/ → backend minor bump
- `fix:` in frontend/ → frontend patch bump
- Foundation for future automation

---

## 🏗️ Architecture Design

### Versioning Scheme

**Format:** `0.MINOR.PATCH` (Alpha Phase)

**Semantic Versioning Rules (Alpha):**
```
0.MINOR.PATCH where:
  MINOR: Incremented for features, breaking changes (anything significant)
  PATCH: Incremented for bug fixes, documentation, refactors

Examples:
  0.1.0 → 0.2.0  (new feature added)
  0.2.0 → 0.2.1  (bug fix)
  0.2.1 → 0.3.0  (breaking API change)
```

**Why 0.x.x Format:**
- Semantic Versioning 2.0.0 specification: "Major version zero (0.y.z) is for initial development. Anything MAY change at any time."
- Communicates: "API not stable, expect changes"
- Can stay in 0.x.x indefinitely until team decides to release 1.0.0

**Component-Specific Versioning:**

| Component | Current | Initial Target | Location |
|-----------|---------|---------------|----------|
| **Backend API** | 0.1.0 | 0.1.0 | `backend/pyproject.toml` |
| **Frontend** | 0.0.0 | 0.1.0 | `frontend/package.json` |
| **Database Schema** | none | 0.1.0 | `backend/app/models/schema_version.py` |

**Version Synchronization Strategy:**
- ✅ **Independent by default:** Each component versions independently
- ❌ **No forced sync:** Backend and frontend don't need to match
- ⚠️ **Optional sync:** `make bump-all-minor` available for major milestones

---

## 🔍 Prior Art & Best Practices Analysis

### Industry Standards (2025)

**1. Monorepo Versioning Approaches**

**Option A: Independent Versioning (RECOMMENDED)**
- **Tools:** Lerna (independent mode), Nx, Changesets
- **Example:** `backend@0.5.2`, `frontend@0.8.1`
- **Pros:** Maximum flexibility, components evolve independently
- **Cons:** More complex to track (mitigated by /version endpoint)
- **Used by:** React, Babel, Vue ecosystem

**Option B: Synchronized Versioning**
- **Example:** All components share version `0.3.0`
- **Pros:** Simple to communicate, clear release milestones
- **Cons:** Forces unnecessary version bumps, couples unrelated changes
- **Used by:** Smaller projects, tightly coupled systems

**Decision:** **Independent versioning** - our backend and frontend are sufficiently decoupled

**2. Conventional Commits Standard**

**Specification:** https://www.conventionalcommits.org/

**Format:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat:` - New feature → **MINOR** bump
- `fix:` - Bug fix → **PATCH** bump
- `docs:` - Documentation → **PATCH** bump
- `refactor:` - Code refactor → **PATCH** bump
- `perf:` - Performance improvement → **PATCH** bump
- `test:` - Tests → **PATCH** bump
- `chore:` - Build/tooling → No version bump
- `BREAKING CHANGE:` in footer → **MINOR** bump (in 0.x.x) / **MAJOR** bump (in 1.x.x+)

**Examples:**
```bash
# Backend feature - bump backend minor version
feat(backend/api): add HPO classifications endpoint

# Frontend bugfix - bump frontend patch version
fix(frontend): network graph not rendering with >500 genes

# Database migration - bump database minor version
feat(backend/db): add gene_hpo_classifications view

# Documentation - bump relevant patch version
docs(backend): update API documentation for genes endpoint
```

**3. Automation Tools Research**

**Manual Approach (Phase 1 - RECOMMENDED):**
- Make commands: `make bump-backend-minor`
- Updates `pyproject.toml` / `package.json`
- Creates git tag: `backend/v0.2.0`
- Simple, no external dependencies

**Automated Approach (Phase 2 - FUTURE):**
- **semantic-release:** Fully automated, analyzes commits
- **Changesets:** Human-in-the-loop, great for monorepos
- **Nx Release:** Integrated with Nx build system
- **Lerna:** Classic monorepo tool

**Decision:** Start manual (Phase 1), automate later when value is proven

---

## 📐 Detailed Implementation Plan

### Phase 1: Core Infrastructure (6 hours)

#### 1.1 Database Version Tracking (2 hours)

**Step 1: Create SchemaVersion Model**

**File:** `backend/app/models/schema_version.py`

```python
"""
Database schema version tracking model.

Tracks schema versions and migration history for debugging and rollback.
Each Alembic migration automatically creates a schema_version record.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.base_class import Base


class SchemaVersion(Base):
    """
    Schema version tracking table.

    Stores version history for database schema changes.
    Links to Alembic revisions for migration management.
    """
    __tablename__ = "schema_versions"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(
        String(20),
        unique=True,
        nullable=False,
        comment="Semantic version (e.g., 0.1.0)"
    )
    alembic_revision = Column(
        String(50),
        nullable=False,
        comment="Alembic migration revision ID"
    )
    description = Column(
        Text,
        nullable=True,
        comment="Human-readable description of changes"
    )
    applied_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp when version was applied"
    )

    def __repr__(self):
        return f"<SchemaVersion(version='{self.version}', revision='{self.alembic_revision}')>"
```

**Step 2: Update Models Index**

**File:** `backend/app/models/__init__.py`

```python
# Add to existing imports
from app.models.schema_version import SchemaVersion

# Add to __all__ list
__all__ = [
    # ... existing models ...
    "SchemaVersion",
]
```

**Step 3: Create Alembic Migration**

```bash
cd backend
uv run alembic revision --autogenerate -m "Add schema_versions table for version tracking"
```

**Step 4: Enhance Migration Template** (Optional - for future automation)

Edit generated migration to automatically create version record:

```python
"""Add schema_versions table for version tracking

Revision ID: abc123def456
Create Date: 2025-01-10 10:00:00
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# Current schema version
SCHEMA_VERSION = "0.1.0"

def upgrade():
    # Create schema_versions table
    op.create_table(
        'schema_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('version', sa.String(20), unique=True, nullable=False),
        sa.Column('alembic_revision', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=False),
    )

    # Insert initial version record
    op.execute(f"""
        INSERT INTO schema_versions (version, alembic_revision, description, applied_at)
        VALUES (
            '{SCHEMA_VERSION}',
            '{op.get_bind().execute("SELECT version_num FROM alembic_version").scalar()}',
            'Initial schema version tracking',
            '{datetime.utcnow().isoformat()}'
        )
    """)

def downgrade():
    op.drop_table('schema_versions')
```

**Step 5: Apply Migration**

```bash
cd backend
uv run alembic upgrade head
```

#### 1.2 Backend Version Management (1.5 hours)

**Step 1: Verify Current Version**

**File:** `backend/pyproject.toml`

```toml
[project]
name = "kidney-genetics-db"
version = "0.1.0"  # ✅ Already correct
description = "Modern web platform for curating and exploring kidney disease-related genes"
# ... rest of config
```

**Step 2: Create Version Utility Module**

**File:** `backend/app/core/version.py`

```python
"""
Application version management utilities.

Provides centralized access to component versions for API responses,
logging, and monitoring.
"""

import os
import importlib.metadata
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_package_version() -> str:
    """
    Get backend package version from installed metadata.

    Returns:
        Version string (e.g., "0.1.0")
    """
    try:
        # Get version from installed package metadata
        return importlib.metadata.version("kidney-genetics-db")
    except importlib.metadata.PackageNotFoundError:
        logger.sync_warning("Package metadata not found, reading from pyproject.toml")
        # Fallback: parse pyproject.toml directly
        try:
            import toml
            pyproject_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "pyproject.toml"
            )
            with open(pyproject_path, "r") as f:
                data = toml.load(f)
                return data["project"]["version"]
        except Exception as e:
            logger.sync_error(f"Failed to read version: {e}")
            return "unknown"


def get_database_version(db: Session) -> Optional[dict]:
    """
    Get latest database schema version from schema_versions table.

    Args:
        db: Database session

    Returns:
        Dict with version info or None if no versions found
        {
            "version": "0.1.0",
            "alembic_revision": "abc123def456",
            "description": "Initial schema",
            "applied_at": "2025-01-10T10:00:00"
        }
    """
    try:
        result = db.execute(
            text("""
                SELECT version, alembic_revision, description, applied_at
                FROM schema_versions
                ORDER BY applied_at DESC
                LIMIT 1
            """)
        ).fetchone()

        if result:
            return {
                "version": result.version,
                "alembic_revision": result.alembic_revision,
                "description": result.description,
                "applied_at": result.applied_at.isoformat() if result.applied_at else None
            }
        return None
    except Exception as e:
        logger.sync_error(f"Failed to get database version: {e}")
        return None


def get_all_versions(db: Session) -> dict:
    """
    Get versions for all components.

    Args:
        db: Database session

    Returns:
        Dict with all component versions and environment info
    """
    backend_version = get_package_version()
    db_version = get_database_version(db)

    return {
        "backend": {
            "version": backend_version,
            "name": "kidney-genetics-db",
            "type": "FastAPI"
        },
        "database": db_version or {"version": "unknown"},
        "environment": os.getenv("ENV", "development"),
        "timestamp": datetime.utcnow().isoformat()
    }
```

**Step 3: Create Version API Endpoint**

**File:** `backend/app/api/endpoints/version.py`

```python
"""
Version information endpoint.

Provides version information for all components (backend, frontend, database).
Public endpoint, no authentication required.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.version import get_all_versions
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/version")
async def get_version(db: Session = Depends(get_db)) -> dict:
    """
    Get version information for all components.

    Returns version details for:
    - Backend API
    - Database schema
    - Environment information

    Public endpoint - no authentication required.

    Returns:
        {
            "backend": {
                "version": "0.1.0",
                "name": "kidney-genetics-db",
                "type": "FastAPI"
            },
            "database": {
                "version": "0.1.0",
                "alembic_revision": "abc123",
                "description": "Initial schema",
                "applied_at": "2025-01-10T10:00:00"
            },
            "environment": "production",
            "timestamp": "2025-01-10T12:00:00"
        }
    """
    await logger.info("Version information requested")

    versions = get_all_versions(db)

    await logger.debug(
        "Version info returned",
        backend_version=versions["backend"]["version"],
        database_version=versions["database"].get("version", "unknown")
    )

    return versions
```

**Step 4: Register Version Endpoint**

**File:** `backend/app/api/api.py`

```python
# Add import
from app.api.endpoints import version

# Add router registration (in api_router)
api_router.include_router(
    version.router,
    tags=["system"]
)
```

#### 1.3 Frontend Version Management (1.5 hours)

**Step 1: Update Frontend Version**

**File:** `frontend/package.json`

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.1.0",  // CHANGE from 0.0.0 to 0.1.0
  "type": "module",
  // ... rest of config
}
```

**Step 2: Create Version Utility**

**File:** `frontend/src/utils/version.js`

```javascript
/**
 * Version management utilities
 *
 * Provides access to component versions for display in UI.
 * Fetches backend/database versions from API.
 */

import api from '@/services/api'

/**
 * Get frontend version from package.json
 * @returns {string} Frontend version (e.g., "0.1.0")
 */
export function getFrontendVersion() {
  // Injected by Vite at build time
  return __APP_VERSION__
}

/**
 * Get all component versions from backend API
 * @returns {Promise<Object>} Version information for all components
 */
export async function getAllVersions() {
  try {
    const response = await api.get('/version')

    // Add frontend version to response
    return {
      ...response.data,
      frontend: {
        version: getFrontendVersion(),
        name: 'kidney-genetics-db-frontend',
        type: 'Vue.js'
      }
    }
  } catch (error) {
    console.error('Failed to fetch versions:', error)

    // Fallback: return only frontend version
    return {
      frontend: {
        version: getFrontendVersion(),
        name: 'kidney-genetics-db-frontend',
        type: 'Vue.js'
      },
      backend: { version: 'unknown' },
      database: { version: 'unknown' }
    }
  }
}
```

**Step 3: Configure Vite to Inject Version**

**File:** `frontend/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath } from 'url'
import { readFileSync } from 'fs'

// Read version from package.json
const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
)

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  define: {
    // Inject version as global constant
    __APP_VERSION__: JSON.stringify(packageJson.version)
  }
})
```

**Step 4: Create Version Display Component**

**File:** `frontend/src/components/AppFooter.vue`

```vue
<template>
  <v-footer app class="bg-grey-lighten-4 px-4 py-2">
    <v-container fluid>
      <v-row align="center" justify="space-between" dense>
        <!-- Project Info -->
        <v-col cols="12" md="6" class="text-center text-md-left">
          <span class="text-caption text-medium-emphasis">
            © {{ currentYear }} Kidney Genetics Database
          </span>
          <v-divider vertical class="mx-2 d-none d-md-inline-block" />
          <a
            href="https://github.com/berntpopp/kidney-genetics-db"
            target="_blank"
            class="text-caption text-decoration-none text-primary"
          >
            <v-icon icon="mdi-github" size="small" class="mr-1" />
            GitHub
          </a>
        </v-col>

        <!-- Version Info -->
        <v-col cols="12" md="6" class="text-center text-md-right">
          <v-menu location="top">
            <template #activator="{ props }">
              <v-btn
                v-bind="props"
                variant="text"
                size="small"
                density="compact"
                class="text-caption"
              >
                <v-icon icon="mdi-information-outline" size="small" class="mr-1" />
                v{{ versions.frontend.version }}
                <v-icon icon="mdi-chevron-up" size="small" class="ml-1" />
              </v-btn>
            </template>

            <v-card min-width="300">
              <v-card-title class="text-subtitle-2 bg-primary">
                Component Versions
              </v-card-title>

              <v-card-text class="pa-0">
                <v-list density="compact" lines="two">
                  <!-- Frontend -->
                  <v-list-item>
                    <template #prepend>
                      <v-icon icon="mdi-view-dashboard" color="primary" />
                    </template>
                    <v-list-item-title>Frontend</v-list-item-title>
                    <v-list-item-subtitle>
                      v{{ versions.frontend.version }} ({{ versions.frontend.type }})
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-divider />

                  <!-- Backend -->
                  <v-list-item>
                    <template #prepend>
                      <v-icon icon="mdi-server" color="success" />
                    </template>
                    <v-list-item-title>Backend API</v-list-item-title>
                    <v-list-item-subtitle>
                      v{{ versions.backend.version }} ({{ versions.backend.type }})
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-divider />

                  <!-- Database -->
                  <v-list-item>
                    <template #prepend>
                      <v-icon icon="mdi-database" color="warning" />
                    </template>
                    <v-list-item-title>Database Schema</v-list-item-title>
                    <v-list-item-subtitle v-if="versions.database.version !== 'unknown'">
                      v{{ versions.database.version }}
                      <span v-if="versions.database.applied_at" class="text-caption">
                        ({{ formatDate(versions.database.applied_at) }})
                      </span>
                    </v-list-item-subtitle>
                    <v-list-item-subtitle v-else class="text-error">
                      Unknown
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-divider />

                  <!-- Environment -->
                  <v-list-item>
                    <template #prepend>
                      <v-icon
                        :icon="environmentIcon"
                        :color="environmentColor"
                      />
                    </template>
                    <v-list-item-title>Environment</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ versions.environment || 'development' }}
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>

              <v-card-actions>
                <v-spacer />
                <v-btn
                  size="small"
                  variant="text"
                  @click="refreshVersions"
                  :loading="loading"
                >
                  <v-icon icon="mdi-refresh" size="small" class="mr-1" />
                  Refresh
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-menu>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getAllVersions } from '@/utils/version'

// State
const versions = ref({
  frontend: { version: 'loading...', type: 'Vue.js' },
  backend: { version: 'loading...', type: 'FastAPI' },
  database: { version: 'loading...' },
  environment: 'development'
})
const loading = ref(false)

// Computed
const currentYear = computed(() => new Date().getFullYear())

const environmentIcon = computed(() => {
  const env = versions.value.environment?.toLowerCase()
  return env === 'production' ? 'mdi-cloud-check' :
         env === 'staging' ? 'mdi-cloud-sync' :
         'mdi-laptop'
})

const environmentColor = computed(() => {
  const env = versions.value.environment?.toLowerCase()
  return env === 'production' ? 'success' :
         env === 'staging' ? 'warning' :
         'info'
})

// Methods
async function fetchVersions() {
  loading.value = true
  try {
    const data = await getAllVersions()
    versions.value = data
  } catch (error) {
    console.error('Failed to fetch versions:', error)
  } finally {
    loading.value = false
  }
}

async function refreshVersions() {
  await fetchVersions()
}

function formatDate(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Lifecycle
onMounted(() => {
  fetchVersions()
})
</script>

<style scoped>
.v-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.12);
}
</style>
```

**Step 5: Add Footer to App Layout**

**File:** `frontend/src/App.vue`

```vue
<template>
  <v-app>
    <!-- Existing nav/header -->
    <v-navigation-drawer>
      <!-- ... -->
    </v-navigation-drawer>

    <v-app-bar>
      <!-- ... -->
    </v-app-bar>

    <!-- Main content -->
    <v-main>
      <router-view />
    </v-main>

    <!-- NEW: Add footer -->
    <AppFooter />
  </v-app>
</template>

<script setup>
import AppFooter from '@/components/AppFooter.vue'
// ... existing imports
</script>
```

#### 1.4 Makefile Version Commands (1 hour)

**File:** `Makefile` (add to existing file)

```makefile
# ════════════════════════════════════════════════════════════════════
# VERSION MANAGEMENT
# ════════════════════════════════════════════════════════════════════

.PHONY: version version-backend version-frontend version-database \
        bump-backend-minor bump-backend-patch \
        bump-frontend-minor bump-frontend-patch \
        bump-all-minor bump-all-patch

# Show all component versions
version:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║                    COMPONENT VERSIONS                           ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 Backend API:"
	@cd backend && uv run python -c "\
import toml; \
data = toml.load('pyproject.toml'); \
print(f\"   Version: {data['project']['version']}\")"
	@echo ""
	@echo "🖥️  Frontend:"
	@cd frontend && node -p "\
const pkg = require('./package.json'); \
console.log('   Version: ' + pkg.version); ''"
	@echo ""
	@echo "🗄️  Database Schema:"
	@-cd backend && uv run python -c "\
from sqlalchemy import create_engine, text; \
from app.core.config import settings; \
try: \
    engine = create_engine(settings.DATABASE_URL); \
    with engine.connect() as conn: \
        result = conn.execute(text('SELECT version, applied_at FROM schema_versions ORDER BY applied_at DESC LIMIT 1')).fetchone(); \
        if result: \
            print(f'   Version: {result.version}'); \
            print(f'   Applied: {result.applied_at}'); \
        else: \
            print('   Version: Not initialized'); \
except Exception as e: \
    print('   Version: Database not accessible');" 2>/dev/null || echo "   Database not accessible"

# Bump backend minor version (0.1.0 → 0.2.0)
bump-backend-minor:
	@echo "🔼 Bumping backend MINOR version..."
	@cd backend && uv run python -c "\
import toml; \
data = toml.load('pyproject.toml'); \
version_parts = data['project']['version'].split('.'); \
new_version = f'{version_parts[0]}.{int(version_parts[1]) + 1}.0'; \
data['project']['version'] = new_version; \
with open('pyproject.toml', 'w') as f: \
    toml.dump(data, f); \
print(f'✅ Backend version bumped to {new_version}')"
	@echo "📝 Don't forget to commit and tag: git tag backend/v$$(cd backend && uv run python -c 'import toml; print(toml.load(\"pyproject.toml\")[\"project\"][\"version\"])')"

# Bump backend patch version (0.1.0 → 0.1.1)
bump-backend-patch:
	@echo "🔼 Bumping backend PATCH version..."
	@cd backend && uv run python -c "\
import toml; \
data = toml.load('pyproject.toml'); \
version_parts = data['project']['version'].split('.'); \
new_version = f'{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}'; \
data['project']['version'] = new_version; \
with open('pyproject.toml', 'w') as f: \
    toml.dump(data, f); \
print(f'✅ Backend version bumped to {new_version}')"
	@echo "📝 Don't forget to commit and tag: git tag backend/v$$(cd backend && uv run python -c 'import toml; print(toml.load(\"pyproject.toml\")[\"project\"][\"version\"])')"

# Bump frontend minor version (0.1.0 → 0.2.0)
bump-frontend-minor:
	@echo "🔼 Bumping frontend MINOR version..."
	@cd frontend && npm version minor --no-git-tag-version
	@echo "✅ Frontend version bumped to $$(cd frontend && node -p 'require(\"./package.json\").version')"
	@echo "📝 Don't forget to commit and tag: git tag frontend/v$$(cd frontend && node -p 'require(\"./package.json\").version')"

# Bump frontend patch version (0.1.0 → 0.1.1)
bump-frontend-patch:
	@echo "🔼 Bumping frontend PATCH version..."
	@cd frontend && npm version patch --no-git-tag-version
	@echo "✅ Frontend version bumped to $$(cd frontend && node -p 'require(\"./package.json\").version')"
	@echo "📝 Don't forget to commit and tag: git tag frontend/v$$(cd frontend && node -p 'require(\"./package.json\").version')"

# Bump all components minor version (for major milestones)
bump-all-minor: bump-backend-minor bump-frontend-minor
	@echo ""
	@echo "✅ All components bumped to minor versions"
	@echo "📝 Next steps:"
	@echo "   1. git add backend/pyproject.toml frontend/package.json"
	@echo "   2. git commit -m 'chore: bump all versions for [milestone name]'"
	@echo "   3. git tag -a v$$(cd backend && uv run python -c 'import toml; print(toml.load(\"pyproject.toml\")[\"project\"][\"version\"])') -m 'Release [milestone name]'"

# Bump all components patch version (for bug fix releases)
bump-all-patch: bump-backend-patch bump-frontend-patch
	@echo ""
	@echo "✅ All components bumped to patch versions"
	@echo "📝 Next steps:"
	@echo "   1. git add backend/pyproject.toml frontend/package.json"
	@echo "   2. git commit -m 'chore: bump all versions for bug fixes'"
	@echo "   3. git tag -a v$$(cd backend && uv run python -c 'import toml; print(toml.load(\"pyproject.toml\")[\"project\"][\"version\"])') -m 'Bug fix release'"
```

**Update Help Target:**

```makefile
help:
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║         Kidney Genetics Database - Development Commands         ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	# ... existing sections ...
	@echo "📌 VERSION MANAGEMENT:"
	@echo "  make version             - Show all component versions"
	@echo "  make bump-backend-minor  - Bump backend minor version (0.1.0 → 0.2.0)"
	@echo "  make bump-backend-patch  - Bump backend patch version (0.1.0 → 0.1.1)"
	@echo "  make bump-frontend-minor - Bump frontend minor version"
	@echo "  make bump-frontend-patch - Bump frontend patch version"
	@echo "  make bump-all-minor      - Bump all components (major milestone)"
	@echo "  make bump-all-patch      - Bump all components (bug fixes)"
	@echo ""
	# ... rest of help
```

---

### Phase 2: Conventional Commits Integration (3 hours)

#### 2.1 Conventional Commits Setup (1 hour)

**Step 1: Install Commitlint**

```bash
# Install commitlint for commit message validation
cd frontend  # or root if using npm workspaces
npm install -D @commitlint/cli @commitlint/config-conventional

# Create commitlint config
cat > commitlint.config.js << 'EOF'
/**
 * Commitlint configuration
 *
 * Enforces conventional commits standard for automatic versioning.
 * See: https://www.conventionalcommits.org/
 */

module.exports = {
  extends: ['@commitlint/config-conventional'],

  rules: {
    // Type enum - what types of commits we allow
    'type-enum': [
      2,
      'always',
      [
        'feat',      // New feature → MINOR bump
        'fix',       // Bug fix → PATCH bump
        'docs',      // Documentation → PATCH bump
        'style',     // Formatting → PATCH bump
        'refactor',  // Code refactor → PATCH bump
        'perf',      // Performance → PATCH bump
        'test',      // Tests → PATCH bump
        'chore',     // Build/tooling → No bump
        'ci',        // CI config → No bump
        'revert'     // Revert commit → Depends
      ]
    ],

    // Scope enum - which components can be affected
    'scope-enum': [
      1,  // Warning level (not blocking)
      'always',
      [
        'backend',
        'frontend',
        'database',
        'docs',
        'api',
        'ui',
        'pipeline',
        'admin',
        'network',
        'auth'
      ]
    ],

    // Subject case - should be lowercase
    'subject-case': [2, 'always', 'lower-case'],

    // Subject empty - must have subject
    'subject-empty': [2, 'never'],

    // Subject full-stop - no period at end
    'subject-full-stop': [2, 'never', '.'],

    // Body leading blank - blank line after subject
    'body-leading-blank': [1, 'always'],

    // Footer leading blank - blank line before footer
    'footer-leading-blank': [1, 'always']
  }
}
EOF
```

**Step 2: Install Husky for Git Hooks**

```bash
cd frontend
npm install -D husky

# Initialize husky
npx husky init

# Create commit-msg hook
cat > .husky/commit-msg << 'EOF'
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

# Validate commit message with commitlint
npx --no-install commitlint --edit $1
EOF

chmod +x .husky/commit-msg
```

**Step 3: Add package.json Scripts**

**File:** `frontend/package.json`

```json
{
  "scripts": {
    // ... existing scripts ...
    "prepare": "husky install",
    "commit": "cz"
  },
  "devDependencies": {
    "@commitlint/cli": "^18.0.0",
    "@commitlint/config-conventional": "^18.0.0",
    "husky": "^8.0.3"
  }
}
```

**Step 4: Document Conventional Commits**

**File:** `docs/guides/developer/commit-conventions.md`

```markdown
# Commit Message Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/) specification for consistent commit messages that drive automatic versioning.

## Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

## Types

| Type | Description | Version Bump | Example |
|------|-------------|--------------|---------|
| `feat` | New feature | MINOR | `feat(backend): add version API endpoint` |
| `fix` | Bug fix | PATCH | `fix(frontend): network graph rendering issue` |
| `docs` | Documentation | PATCH | `docs(api): update genes endpoint docs` |
| `refactor` | Code refactor | PATCH | `refactor(backend): simplify cache service` |
| `perf` | Performance | PATCH | `perf(frontend): optimize gene list rendering` |
| `test` | Tests | PATCH | `test(backend): add version endpoint tests` |
| `chore` | Build/tooling | None | `chore: update dependencies` |

## Scopes

Common scopes:
- `backend` - Backend API changes
- `frontend` - Frontend UI changes
- `database` - Database schema/migrations
- `docs` - Documentation
- `api` - API endpoints
- `ui` - UI components
- `pipeline` - Data pipeline
- `admin` - Admin panel
- `network` - Network analysis
- `auth` - Authentication/authorization

## Examples

### Good Commits

```bash
# Feature with scope
feat(backend/api): add HPO classifications endpoint

# Bug fix with scope
fix(frontend/network): graph not rendering with >500 genes

# Breaking change (still minor in 0.x.x)
feat(backend)!: change genes API response format

BREAKING CHANGE: Genes API now returns JSON:API format

# Documentation
docs(backend): add version management guide

# Chore (no version bump)
chore(deps): update dependencies
```

### Bad Commits (Will Be Rejected)

```bash
# ❌ No type
Add version endpoint

# ❌ Capital letter in subject
feat(backend): Add version endpoint

# ❌ Period at end
feat(backend): add version endpoint.

# ❌ Vague subject
fix: bug

# ❌ Invalid type
feature: add endpoint
```

## Enforcement

Commit messages are validated automatically via `commitlint` on `commit-msg` git hook. Invalid commits will be rejected.

## Future Automation

These commit messages will drive:
- Automatic version bumping (Phase 2)
- Changelog generation
- Release notes
```

#### 2.2 Git Tagging Strategy (1 hour)

**Documentation:**

**File:** `docs/guides/developer/version-tagging.md`

```markdown
# Version Tagging Strategy

## Tag Format

**Component-specific tags:**
```
backend/v<version>    # Backend releases
frontend/v<version>   # Frontend releases
database/v<version>   # Database schema versions
```

**Unified tags (for major milestones):**
```
v<version>  # Unified release (optional)
```

## Examples

```bash
# Backend release
git tag -a backend/v0.2.0 -m "feat: Add version tracking and HPO endpoints"
git push origin backend/v0.2.0

# Frontend release
git tag -a frontend/v0.3.0 -m "feat: Add network analysis URL state management"
git push origin frontend/v0.3.0

# Database migration
git tag -a database/v0.2.0 -m "feat: Add schema_versions table"
git push origin database/v0.2.0

# Unified milestone (optional)
git tag -a v0.2.0 -m "Release: Version tracking system complete"
git push origin v0.2.0
```

## Workflow

### Manual Tagging (Current)

1. **Bump version:** `make bump-backend-minor`
2. **Commit changes:** `git add backend/pyproject.toml && git commit -m "chore(backend): bump to v0.2.0"`
3. **Create tag:** `git tag -a backend/v0.2.0 -m "Release v0.2.0"`
4. **Push tag:** `git push origin backend/v0.2.0`

### Automated Tagging (Future)

GitHub Actions will automatically:
1. Detect conventional commits in backend/
2. Bump version in pyproject.toml
3. Create git tag
4. Generate release notes
```

#### 2.3 Changelog Generation (1 hour)

**Install Changelog Tool:**

```bash
cd frontend
npm install -D conventional-changelog-cli
```

**Add Scripts:**

**File:** `frontend/package.json`

```json
{
  "scripts": {
    "changelog": "conventional-changelog -p angular -i CHANGELOG.md -s",
    "changelog:all": "conventional-changelog -p angular -i CHANGELOG.md -s -r 0"
  }
}
```

**Create Initial Changelog:**

**File:** `CHANGELOG.md`

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Version tracking system for backend, frontend, and database
- API endpoint `/version` for version information
- Footer component displaying all component versions
- Make commands for version management

## [0.1.0] - 2025-01-10

### Added
- Initial alpha release
- Core gene database functionality
- Network analysis features
- Admin panel with user management
```

---

### Phase 3: Future Automation (3 hours - OPTIONAL)

This phase can be implemented later when the manual process is proven.

#### 3.1 GitHub Actions Workflow (2 hours)

**File:** `.github/workflows/version-bump.yml`

```yaml
name: Automated Version Bumping

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - 'frontend/**'

jobs:
  check-version-bump:
    name: Check if Version Bump Needed
    runs-on: ubuntu-latest
    outputs:
      backend-bump: ${{ steps.check.outputs.backend-bump }}
      frontend-bump: ${{ steps.check.outputs.frontend-bump }}

    steps:
      - name: Checkout
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for commit analysis

      - name: Analyze Commits
        id: check
        run: |
          # Get commits since last tag
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

          # Check backend commits
          BACKEND_COMMITS=$(git log ${LAST_TAG}..HEAD --oneline -- backend/ | grep -E '^[a-f0-9]+ (feat|fix):' || echo "")
          if [ -n "$BACKEND_COMMITS" ]; then
            echo "backend-bump=true" >> $GITHUB_OUTPUT
          fi

          # Check frontend commits
          FRONTEND_COMMITS=$(git log ${LAST_TAG}..HEAD --oneline -- frontend/ | grep -E '^[a-f0-9]+ (feat|fix):' || echo "")
          if [ -n "$FRONTEND_COMMITS" ]; then
            echo "frontend-bump=true" >> $GITHUB_OUTPUT
          fi

  bump-backend:
    name: Bump Backend Version
    runs-on: ubuntu-latest
    needs: check-version-bump
    if: needs.check-version-bump.outputs.backend-bump == 'true'

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Bump Version
        run: make bump-backend-minor

      - name: Create Tag
        run: |
          VERSION=$(cd backend && python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
          git tag -a "backend/v${VERSION}" -m "chore: Automated backend version bump to ${VERSION}"
          git push origin "backend/v${VERSION}"

  bump-frontend:
    name: Bump Frontend Version
    runs-on: ubuntu-latest
    needs: check-version-bump
    if: needs.check-version-bump.outputs.frontend-bump == 'true'

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Bump Version
        run: make bump-frontend-minor

      - name: Create Tag
        run: |
          VERSION=$(cd frontend && node -p "require('./package.json').version")
          git tag -a "frontend/v${VERSION}" -m "chore: Automated frontend version bump to ${VERSION}"
          git push origin "frontend/v${VERSION}"
```

#### 3.2 Release Notes Generation (1 hour)

**File:** `.github/workflows/release-notes.yml`

```yaml
name: Generate Release Notes

on:
  push:
    tags:
      - 'backend/v*'
      - 'frontend/v*'
      - 'v*'

jobs:
  release-notes:
    name: Generate Release Notes
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Generate Notes
        uses: docker://githubchangeloggenerator/github-changelog-generator:1.16.2
        with:
          args: >-
            --user berntpopp
            --project kidney-genetics-db
            --token ${{ secrets.GITHUB_TOKEN }}
            --since-tag ${{ github.ref_name }}
            --output RELEASE_NOTES.md

      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref_name }}
          release_name: Release ${{ github.ref_name }}
          body_path: RELEASE_NOTES.md
          draft: false
          prerelease: true  # All 0.x.x are pre-releases
```

---

## 🧪 Testing Strategy

### Manual Testing Checklist

**Backend Version Endpoint:**
- [ ] `curl http://localhost:8000/api/version` returns correct JSON
- [ ] Backend version matches pyproject.toml
- [ ] Database version matches schema_versions table
- [ ] Environment is correctly identified

**Frontend Footer:**
- [ ] Footer displays on all pages
- [ ] Version menu opens on click
- [ ] All component versions displayed correctly
- [ ] Refresh button works
- [ ] Loading states appear correctly

**Make Commands:**
- [ ] `make version` shows all versions
- [ ] `make bump-backend-minor` increments minor version
- [ ] `make bump-backend-patch` increments patch version
- [ ] `make bump-frontend-minor` works correctly
- [ ] `make bump-frontend-patch` works correctly
- [ ] `make bump-all-minor` bumps all components

**Git Workflow:**
- [ ] Conventional commit messages validated
- [ ] Invalid commits rejected
- [ ] Git tags created correctly
- [ ] Tags pushed to remote successfully

### API Testing

**File:** `backend/tests/api/test_version.py`

```python
"""
Tests for version API endpoint.
"""

import pytest
from fastapi.testclient import TestClient


def test_version_endpoint_structure(client: TestClient):
    """Test version endpoint returns correct structure."""
    response = client.get("/api/version")

    assert response.status_code == 200
    data = response.json()

    # Check top-level keys
    assert "backend" in data
    assert "database" in data
    assert "environment" in data
    assert "timestamp" in data

    # Check backend structure
    assert "version" in data["backend"]
    assert "name" in data["backend"]
    assert "type" in data["backend"]

    # Validate version format (0.x.x)
    backend_version = data["backend"]["version"]
    assert backend_version.startswith("0."), \
        "Version should be in alpha format (0.x.x)"


def test_version_matches_package(client: TestClient):
    """Test API version matches package version."""
    import importlib.metadata

    response = client.get("/api/version")
    data = response.json()

    package_version = importlib.metadata.version("kidney-genetics-db")
    api_version = data["backend"]["version"]

    assert api_version == package_version, \
        "API version should match package metadata"


def test_version_caching(client: TestClient):
    """Test version endpoint can be called multiple times."""
    # Call multiple times - should be fast and consistent
    responses = [client.get("/api/version") for _ in range(5)]

    # All successful
    assert all(r.status_code == 200 for r in responses)

    # All return same version
    versions = [r.json()["backend"]["version"] for r in responses]
    assert len(set(versions)) == 1, "Version should be consistent"
```

---

## 📊 Success Metrics

### Functional Requirements

- ✅ Backend version tracked in pyproject.toml
- ✅ Frontend version tracked in package.json
- ✅ Database version tracked in schema_versions table
- ✅ API endpoint returns all versions
- ✅ UI footer displays versions
- ✅ Make commands work for version bumping
- ✅ Conventional commits validated
- ✅ Git tags created correctly

### Performance Requirements

- ✅ Version API endpoint responds <50ms
- ✅ Footer component loads without flash
- ✅ Version info cached in frontend
- ✅ No performance impact on existing features

### User Experience Requirements

- ✅ Versions clearly visible in UI
- ✅ Admin can check versions easily
- ✅ Developers have clear workflow
- ✅ Version bumping is foolproof

---

## 📚 Documentation Updates

**Files to Update:**

1. **CLAUDE.md**
   ```markdown
   ## Current Status
   - **Production**: Alpha v0.1.0
   - **Versioning**: Independent semantic versioning per component
   - **Version bumping**: `make bump-*` commands
   ```

2. **README.md**
   ```markdown
   ## Version Management

   Check versions:
   ```bash
   make version
   ```

   Bump versions:
   ```bash
   make bump-backend-minor  # 0.1.0 → 0.2.0
   make bump-frontend-patch  # 0.1.0 → 0.1.1
   ```
   ```

3. **Create:** `docs/guides/developer/versioning.md` (comprehensive guide)

---

## 🚀 Deployment Checklist

### Pre-Deployment

- [ ] All unit tests passing
- [ ] API endpoint tested manually
- [ ] Footer component displays correctly
- [ ] Make commands tested
- [ ] Documentation updated
- [ ] Code reviewed

### Deployment

- [ ] Database migration applied
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] Version endpoint accessible
- [ ] Footer visible to users

### Post-Deployment

- [ ] Monitor error logs
- [ ] Verify versions displayed correctly
- [ ] Test version bumping workflow
- [ ] Collect user feedback

---

## 🎯 Future Enhancements

### Phase 2: Automation (OPTIONAL - Implement Later)

**When to Implement:**
- After 10+ manual version bumps
- When CI/CD pipeline is established
- When team size grows (>3 developers)

**Features:**
- Automatic version bumping via GitHub Actions
- Conventional commits drive versioning
- Automated changelog generation
- Release notes on GitHub Releases
- Semantic-release integration

**Estimated Effort:** 8 hours

### Phase 3: Advanced Features (OPTIONAL)

**Possible Enhancements:**
- Version compatibility checker
- Breaking change detection
- Rollback capability
- Version history UI
- A/B testing support

---

## 📋 Implementation Timeline

### Week 1: Core Infrastructure (6 hours)

**Monday-Tuesday:**
- [ ] Create SchemaVersion model (2h)
- [ ] Create version utility modules (1.5h)
- [ ] Create version API endpoint (1.5h)
- [ ] Write unit tests (1h)

### Week 2: UI & Commands (3 hours)

**Wednesday:**
- [ ] Update frontend package.json (0.5h)
- [ ] Create version utility (0.5h)
- [ ] Create AppFooter component (1.5h)
- [ ] Add to App.vue (0.5h)

**Thursday:**
- [ ] Add Makefile commands (1h)
- [ ] Test all commands (0.5h)
- [ ] Update help text (0.5h)

### Week 3: Conventional Commits (3 hours)

**Friday:**
- [ ] Install commitlint + husky (1h)
- [ ] Create commit conventions doc (1h)
- [ ] Create tagging guide (1h)

### Testing & Deployment

- [ ] Manual testing (2h)
- [ ] Code review (1h)
- [ ] Deployment (1h)

**Total:** 12 hours

---

## 🔄 Migration Path

### Step 1: Initialize Versions

```bash
# 1. Apply database migration
cd backend
uv run alembic upgrade head

# 2. Update frontend version
cd ../frontend
npm version 0.1.0 --no-git-tag-version

# 3. Verify versions
cd ..
make version
```

### Step 2: Test Version Endpoint

```bash
# Start backend
make backend

# Test endpoint (in another terminal)
curl http://localhost:8000/api/version | jq
```

### Step 3: Test Frontend

```bash
# Start frontend
make frontend

# Visit http://localhost:5173
# Check footer in bottom right
```

### Step 4: Commit Everything

```bash
git add .
git commit -m "feat: add version tracking for all components

- Add schema_versions table to database
- Create /version API endpoint
- Add version display in UI footer
- Add Makefile commands for version management
- Set up conventional commits

BREAKING CHANGE: Initial versioning system implementation"

git tag -a v0.1.0 -m "Initial alpha release with version tracking"
git push origin main --tags
```

---

## 🔒 Security Considerations

**Version Disclosure:**
- ✅ Version information is **public** (no security risk)
- ✅ Helps with debugging and support
- ✅ Does not reveal security vulnerabilities

**No Concerns:**
- Version numbers don't leak sensitive data
- No credentials in version info
- Public endpoints don't require authentication

---

## ✅ Acceptance Criteria

### Must Have (Phase 1)

- ✅ Backend version tracked in pyproject.toml
- ✅ Frontend version tracked in package.json
- ✅ Database version tracked in schema_versions table
- ✅ API endpoint `/version` returns all versions
- ✅ UI footer displays all component versions
- ✅ `make version` command shows all versions
- ✅ `make bump-*` commands work correctly

### Should Have (Phase 1)

- ✅ Conventional commits validation
- ✅ Git tagging strategy documented
- ✅ Developer guides created

### Nice to Have (Phase 2+)

- ⏳ Automated version bumping via CI/CD
- ⏳ Automated changelog generation
- ⏳ Release notes automation

---

## 📖 References

**Semantic Versioning:**
- [SemVer 2.0.0](https://semver.org/) - Official specification
- [SemVer FAQ](https://semver.org/#faq) - Common questions

**Conventional Commits:**
- [Conventional Commits](https://www.conventionalcommits.org/) - Specification
- [Commitlint](https://commitlint.js.org/) - Commit message linting

**Monorepo Versioning:**
- [Lerna Independent Mode](https://lerna.js.org/docs/features/version-and-publish#independent-mode)
- [Nx Release](https://nx.dev/docs/guides/nx-release/automatically-version-with-conventional-commits)
- [Changesets](https://github.com/changesets/changesets)

**Project Documentation:**
- [CLAUDE.md](../../../CLAUDE.md) - Project instructions
- [Architecture Overview](../../architecture/README.md)
- [Project Status](../../project-management/status.md)

---

## 👥 Sign-Off

**Plan Status:** ✅ **APPROVED - Ready for Implementation**

**Reviewed By:**
- [x] Senior Full Stack Developer
- [x] Tech Lead
- [ ] Product Manager (optional for this feature)

**Key Decisions:**
1. ✅ **Independent versioning** per component (not synchronized)
2. ✅ **Manual version bumping** initially (automate later)
3. ✅ **Alpha forever** (0.x.x) until explicit 1.0.0 decision
4. ✅ **Simple visibility** (API + footer) without complexity
5. ✅ **Conventional commits** foundation for future automation

**Next Steps:**
1. Create feature branch: `git checkout -b feat/version-tracking-system`
2. Implement Phase 1 (Core Infrastructure)
3. Test thoroughly with `make version` and API endpoint
4. Submit PR with demo screenshots
5. Deploy to staging
6. Deploy to production

---

**Document Status:** ✅ Planning Complete - Ready for Implementation
**Last Updated:** 2025-01-10
**Author:** Senior Full Stack Developer + Claude Code
**Estimated Effort:** 12 hours (Phase 1 only)
**Target:** Alpha Release (Stay 0.x.x)
