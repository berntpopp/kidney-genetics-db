# Database View Management System Proposal

## Executive Summary

To enable successful migration squashing and maintain a clean database schema, we need to implement a systematic approach for managing database views and other non-model objects. This proposal outlines a comprehensive solution based on Alembic best practices.

## Current State Analysis

### Identified Database Views (10 total)
1. **cache_stats** - Cache performance metrics
2. **evidence_source_counts** - Evidence counts by source
3. **evidence_count_percentiles** - Percentile rankings for evidence
4. **evidence_classification_weights** - Weight calculations for classifications
5. **evidence_normalized_scores** - Normalized scoring across sources
6. **combined_evidence_scores** - Aggregated evidence scores
7. **gene_scores** - Final gene scoring calculations
8. **static_evidence_counts** - Static source evidence counts
9. **static_evidence_scores** - Static source scoring
10. **evidence_summary_view** - Summary aggregation view

### View Dependencies
```
Tier 1 (Base Views):
├── evidence_source_counts
├── evidence_classification_weights
├── static_evidence_counts
└── cache_stats

Tier 2 (Dependent on Tier 1):
├── evidence_count_percentiles (depends on evidence_source_counts)
├── evidence_normalized_scores (depends on evidence_classification_weights, evidence_count_percentiles)
└── static_evidence_scores

Tier 3 (Dependent on Tier 2):
├── combined_evidence_scores (depends on evidence_normalized_scores, static_evidence_scores)
└── evidence_summary_view

Tier 4 (Final Aggregation):
└── gene_scores (depends on combined_evidence_scores)
```

## Proposed Solution: ReplaceableObject Pattern

Based on Alembic's cookbook recommendations, implement a versioned view management system:

### 1. Create View Definition Module
`backend/app/db/views.py`

```python
"""Database view definitions as ReplaceableObjects."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReplaceableObject:
    """Represents a database object that can be replaced (views, functions)."""
    name: str
    sqltext: str
    dependencies: list[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


# Tier 1 Views (No dependencies)
evidence_source_counts = ReplaceableObject(
    "evidence_source_counts",
    """
    SELECT
        ge.id AS evidence_id,
        ge.gene_id,
        g.approved_symbol,
        ge.source_name,
        CASE ge.source_name
            WHEN 'PanelApp' THEN COALESCE(jsonb_array_length(ge.evidence_data->'panels'), 0)
            WHEN 'HPO' THEN COALESCE(jsonb_array_length(ge.evidence_data->'hpo_terms'), 0) 
                + COALESCE(jsonb_array_length(ge.evidence_data->'diseases'), 0)
            WHEN 'PubTator' THEN COALESCE((ge.evidence_data->>'publication_count')::int, 
                jsonb_array_length(ge.evidence_data->'pmids'))
            WHEN 'Literature' THEN COALESCE(jsonb_array_length(ge.evidence_data->'references'), 0)
            ELSE
                CASE
                    WHEN ge.source_name LIKE 'static_%' THEN
                        (SELECT COUNT(DISTINCT ge2.source_detail)
                         FROM gene_evidence ge2
                         WHERE ge2.gene_id = ge.gene_id
                         AND ge2.source_name = ge.source_name)
                    ELSE 0
                END
        END AS source_count
    FROM gene_evidence ge
    JOIN genes g ON ge.gene_id = g.id
    WHERE ge.source_name = ANY(ARRAY['PanelApp', 'HPO', 'PubTator', 'Literature'])
        OR ge.source_name LIKE 'static_%'
    """
)

# Additional views would be defined similarly...
```

### 2. Custom Alembic Operations
`backend/app/db/alembic_ops.py`

```python
"""Custom Alembic operations for views and functions."""

from alembic.operations import Operations, MigrateOperation
from app.db.views import ReplaceableObject


class ReversibleOp(MigrateOperation):
    """Base class for reversible operations."""
    
    def __init__(self, target: ReplaceableObject):
        self.target = target
    
    @classmethod
    def invoke_for_target(cls, operations, target):
        op = cls(target)
        return operations.invoke(op)
    
    def reverse(self):
        raise NotImplementedError()
    
    @classmethod
    def replace(cls, operations, target, replaces=None, replace_with=None):
        if replaces:
            old_obj = cls._get_object_from_version(operations, replaces)
            drop_old = cls(old_obj).reverse()
            create_new = cls(target)
        elif replace_with:
            old_obj = cls._get_object_from_version(operations, replace_with)
            drop_old = cls(target).reverse()
            create_new = cls(old_obj)
        else:
            raise TypeError("replaces or replace_with is required")
        
        operations.invoke(drop_old)
        operations.invoke(create_new)
    
    @classmethod
    def _get_object_from_version(cls, operations, ident):
        version, objname = ident.split(".")
        module = operations.get_context().script.get_revision(version).module
        obj = getattr(module, objname)
        return obj


@Operations.register_operation("create_view", "invoke_for_target")
@Operations.register_operation("replace_view", "replace")
class CreateViewOp(ReversibleOp):
    def reverse(self):
        return DropViewOp(self.target)


@Operations.register_operation("drop_view", "invoke_for_target")
class DropViewOp(ReversibleOp):
    def reverse(self):
        return CreateViewOp(self.target)


# Implementation functions
@Operations.implementation_for(CreateViewOp)
def create_view(operations, operation):
    operations.execute(f"CREATE VIEW {operation.target.name} AS {operation.target.sqltext}")


@Operations.implementation_for(DropViewOp)
def drop_view(operations, operation):
    operations.execute(f"DROP VIEW IF EXISTS {operation.target.name} CASCADE")
```

### 3. Enhanced env.py Configuration
`backend/alembic/env.py`

```python
# Add to imports
from app.db import alembic_ops  # Register custom operations
from app.db import views as db_views

# Add to run_migrations_online()
def include_object(object, name, type_, reflected, compare_to):
    """Exclude views from autogenerate."""
    # Views are managed separately
    if type_ == "table" and hasattr(object, 'info'):
        return not object.info.get('is_view', False)
    return True

def process_revision_directives(context, revision, directives):
    """Prevent empty migrations and add view management."""
    if getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops and script.upgrade_ops.is_empty():
            # Check if views need updating
            if not check_views_need_update():
                directives[:] = []
                print("No changes detected in models or views.")

# In context.configure()
context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_object=include_object,
    process_revision_directives=process_revision_directives,
    compare_type=True,
    compare_server_default=True,
)
```

### 4. View Version Management
`backend/app/db/view_versions.py`

```python
"""Track view versions for migrations."""

from typing import Dict, List
from app.db.views import ReplaceableObject

VIEW_VERSIONS: Dict[str, List[ReplaceableObject]] = {
    "001_initial": [
        views.evidence_source_counts,
        views.evidence_classification_weights,
        views.evidence_count_percentiles,
        views.evidence_normalized_scores,
        views.gene_scores,
        views.cache_stats,
    ],
    "c6bad0a185f0": [  # Static sources migration
        views.static_evidence_counts,
        views.static_evidence_scores,
    ],
    "7acf7cac5f5f": [  # Combined scoring migration
        views.combined_evidence_scores_v2,  # Updated version
        views.gene_scores_v2,  # Updated to use combined scores
    ],
}

def get_current_views() -> List[ReplaceableObject]:
    """Get the current set of views in dependency order."""
    # Implement topological sort based on dependencies
    pass
```

### 5. Migration Generator Command
`backend/app/cli/db_commands.py`

```python
"""CLI commands for database management."""

import click
from alembic import command
from alembic.config import Config
from app.db.view_versions import get_current_views


@click.command()
@click.option('--message', '-m', required=True, help='Migration message')
def create_view_migration(message):
    """Create a migration for view changes."""
    alembic_cfg = Config("alembic.ini")
    
    # Generate migration with views
    revision_file = command.revision(alembic_cfg, message=message)
    
    # Inject view operations into the migration
    inject_view_operations(revision_file)
    
    click.echo(f"Created migration: {revision_file}")


def inject_view_operations(revision_file):
    """Add view creation/updates to migration file."""
    # Read current views from database
    # Compare with defined views
    # Generate appropriate op.create_view/replace_view calls
    pass
```

## Implementation Steps

### Phase 1: Foundation (Week 1)
1. Create `ReplaceableObject` class and view definitions
2. Implement custom Alembic operations
3. Update env.py with include_object hook
4. Test with simple view creation

### Phase 2: Migration (Week 2)
1. Extract all current view definitions from database
2. Create view definition modules for each view
3. Establish dependency graph
4. Generate initial view migration

### Phase 3: Integration (Week 3)
1. Update existing migrations to use new system
2. Create view version tracking
3. Implement view comparison logic
4. Add CLI commands for view management

### Phase 4: Validation (Week 4)
1. Test complete migration squashing with views
2. Verify view dependencies are maintained
3. Document view update procedures
4. Create view testing framework

## Benefits

1. **Trackable Views**: All views versioned in code
2. **Dependency Management**: Automatic ordering based on dependencies
3. **Reversible Migrations**: Full up/down support for views
4. **Autogenerate Compatible**: Views excluded from autogenerate noise
5. **Squashable Migrations**: Views included in squashed migrations

## Additional Database Object Tracking

### 1. Create Object Registry
`backend/app/db/registry.py`

```python
"""Registry for all database objects."""

from enum import Enum
from typing import Dict, List, Any


class ObjectType(Enum):
    TABLE = "table"
    VIEW = "view"
    FUNCTION = "function"
    TRIGGER = "trigger"
    INDEX = "index"
    CONSTRAINT = "constraint"
    SEQUENCE = "sequence"
    ENUM = "enum"


class DatabaseObject:
    """Base class for database objects."""
    
    def __init__(self, name: str, type_: ObjectType, definition: str):
        self.name = name
        self.type = type_
        self.definition = definition
        self.dependencies = []
        self.metadata = {}


class DatabaseRegistry:
    """Central registry for all database objects."""
    
    def __init__(self):
        self._objects: Dict[str, DatabaseObject] = {}
    
    def register(self, obj: DatabaseObject):
        """Register a database object."""
        self._objects[f"{obj.type.value}:{obj.name}"] = obj
    
    def get_creation_order(self) -> List[DatabaseObject]:
        """Get objects in dependency order."""
        # Topological sort implementation
        pass
    
    def generate_schema(self) -> str:
        """Generate complete schema DDL."""
        pass


# Global registry
registry = DatabaseRegistry()
```

### 2. Object Discovery
`backend/app/db/discovery.py`

```python
"""Discover database objects from various sources."""

from sqlalchemy import inspect
from app.db.registry import registry, DatabaseObject, ObjectType


def discover_from_models(metadata):
    """Discover objects from SQLAlchemy models."""
    for table in metadata.tables.values():
        obj = DatabaseObject(
            name=table.name,
            type_=ObjectType.TABLE,
            definition=str(table.compile())
        )
        registry.register(obj)
        
        # Register indexes
        for index in table.indexes:
            idx_obj = DatabaseObject(
                name=index.name,
                type_=ObjectType.INDEX,
                definition=str(index.compile())
            )
            registry.register(idx_obj)


def discover_from_database(connection):
    """Discover objects from live database."""
    inspector = inspect(connection)
    
    # Discover views
    for view in inspector.get_view_names():
        definition = connection.execute(
            f"SELECT pg_get_viewdef('{view}'::regclass)"
        ).scalar()
        
        obj = DatabaseObject(
            name=view,
            type_=ObjectType.VIEW,
            definition=definition
        )
        registry.register(obj)
```

### 3. Schema Validation
`backend/app/db/validation.py`

```python
"""Validate database schema consistency."""

from app.db.registry import registry
from app.db.discovery import discover_from_database


def validate_schema(connection):
    """Validate that database matches registry."""
    # Discover current database state
    current_objects = discover_from_database(connection)
    
    # Compare with registry
    missing = []
    extra = []
    mismatched = []
    
    # Report discrepancies
    return {
        "missing": missing,
        "extra": extra,
        "mismatched": mismatched,
        "valid": len(missing) == 0 and len(extra) == 0
    }
```

## Testing Strategy

### 1. View Testing Framework
```python
# tests/test_views.py
import pytest
from app.db.views import evidence_source_counts


def test_evidence_source_counts_definition():
    """Test view SQL is valid."""
    assert "gene_evidence" in evidence_source_counts.sqltext
    assert "source_count" in evidence_source_counts.sqltext


def test_view_dependencies():
    """Test dependency graph is correct."""
    from app.db.view_versions import get_current_views
    views = get_current_views()
    
    # Verify no circular dependencies
    # Verify all dependencies exist
```

### 2. Migration Testing
```python
# tests/test_migrations.py
def test_migration_squashing():
    """Test that squashed migration includes all objects."""
    # Create fresh database
    # Apply squashed migration
    # Verify all objects present
    # Compare with original migration chain
```

## Monitoring and Maintenance

### 1. Add Make Commands
```makefile
# View management commands
db-view-check:
	@echo "Checking view consistency..."
	@uv run python -m app.cli.db_commands check-views

db-view-update:
	@echo "Updating view definitions..."
	@uv run python -m app.cli.db_commands update-views

db-view-export:
	@echo "Exporting view definitions..."
	@uv run python -m app.cli.db_commands export-views > views.sql

db-schema-validate:
	@echo "Validating complete schema..."
	@uv run python -m app.cli.db_commands validate-schema
```

### 2. CI/CD Integration
```yaml
# .github/workflows/schema-check.yml
name: Schema Validation
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup database
        run: docker-compose up -d postgres
      - name: Run migrations
        run: make db-migrate
      - name: Validate schema
        run: make db-schema-validate
```

## Migration Path

### Step 1: Implement Core Components
- [ ] Create ReplaceableObject class
- [ ] Define all 10 views as ReplaceableObjects
- [ ] Implement custom Alembic operations
- [ ] Update env.py configuration

### Step 2: Convert Existing Migrations
- [ ] Extract view definitions from current migrations
- [ ] Create view version history
- [ ] Test view creation/updates
- [ ] Validate dependencies

### Step 3: Create Squashed Migration
- [ ] Generate new migration with all tables
- [ ] Add view creation in dependency order
- [ ] Include all indexes and constraints
- [ ] Test on fresh database

### Step 4: Documentation
- [ ] Document view update process
- [ ] Create developer guide
- [ ] Add troubleshooting section
- [ ] Update CLAUDE.md

## Success Criteria

1. **Single Migration File**: Successfully squash to one migration including all objects
2. **View Versioning**: Track and update views through migrations
3. **Dependency Management**: Correct ordering of view creation
4. **Testing Coverage**: 100% of views tested
5. **Developer Experience**: Simple commands for view management

## Conclusion

This comprehensive approach will enable successful migration squashing while maintaining all database objects in a trackable, manageable system. The ReplaceableObject pattern from Alembic's cookbook provides a proven foundation for managing views, while the registry system ensures all database objects are tracked and validated.

---
*Generated: August 22, 2025*
*Status: Proposal - Ready for Review*