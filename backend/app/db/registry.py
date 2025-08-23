"""
Central registry for all database objects to enable comprehensive tracking and validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import inspect, text


class ObjectType(Enum):
    """Types of database objects we track."""

    TABLE = "table"
    VIEW = "view"
    FUNCTION = "function"
    TRIGGER = "trigger"
    INDEX = "index"
    CONSTRAINT = "constraint"
    SEQUENCE = "sequence"
    ENUM = "enum"


@dataclass
class DatabaseObject:
    """Represents any database object that needs tracking."""

    name: str
    type: ObjectType
    definition: str
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema: str = "public"

    @property
    def qualified_name(self) -> str:
        """Return schema-qualified name."""
        if self.schema and self.schema != "public":
            return f"{self.schema}.{self.name}"
        return self.name

    def __hash__(self):
        return hash((self.type.value, self.qualified_name))

    def __eq__(self, other):
        if not isinstance(other, DatabaseObject):
            return False
        return self.type == other.type and self.qualified_name == other.qualified_name


class DatabaseRegistry:
    """Central registry for all database objects."""

    def __init__(self):
        self._objects: dict[str, DatabaseObject] = {}
        self._dependencies: dict[str, list[str]] = {}

    def register(self, obj: DatabaseObject) -> None:
        """Register a database object."""
        key = f"{obj.type.value}:{obj.qualified_name}"
        self._objects[key] = obj

        # Track dependencies
        if obj.dependencies:
            self._dependencies[key] = [f"{ObjectType.VIEW.value}:{dep}" for dep in obj.dependencies]

    def get(self, type: ObjectType, name: str, schema: str = "public") -> DatabaseObject | None:
        """Get a specific database object."""
        qualified_name = f"{schema}.{name}" if schema != "public" else name
        key = f"{type.value}:{qualified_name}"
        return self._objects.get(key)

    def get_all(self, type: ObjectType | None = None) -> list[DatabaseObject]:
        """Get all objects, optionally filtered by type."""
        if type:
            return [obj for key, obj in self._objects.items() if key.startswith(f"{type.value}:")]
        return list(self._objects.values())

    def get_creation_order(self) -> list[DatabaseObject]:
        """Get objects in dependency order using topological sort."""
        visited = set()
        visiting = set()
        sorted_objects = []

        def visit(key: str):
            if key in visited:
                return
            if key in visiting:
                raise ValueError(f"Circular dependency detected involving {key}")

            if key not in self._objects:
                # Dependency not in registry, skip
                return

            visiting.add(key)

            # Visit dependencies first
            for dep_key in self._dependencies.get(key, []):
                visit(dep_key)

            visiting.remove(key)
            visited.add(key)
            sorted_objects.append(self._objects[key])

        # Visit all objects
        for key in self._objects:
            visit(key)

        return sorted_objects

    def get_drop_order(self) -> list[DatabaseObject]:
        """Get objects in reverse dependency order for dropping."""
        return list(reversed(self.get_creation_order()))

    def clear(self) -> None:
        """Clear all registered objects."""
        self._objects.clear()
        self._dependencies.clear()

    def validate_against_database(self, connection) -> dict[str, list[str]]:
        """
        Validate registry against actual database state.

        Returns:
            Dictionary with 'missing', 'extra', and 'mismatched' lists
        """
        inspector = inspect(connection)

        # Get database objects
        db_tables = set(inspector.get_table_names())
        db_views = set(inspector.get_view_names())

        # Get registry objects
        reg_tables = {obj.name for obj in self.get_all(ObjectType.TABLE)}
        reg_views = {obj.name for obj in self.get_all(ObjectType.VIEW)}

        missing_tables = reg_tables - db_tables
        extra_tables = db_tables - reg_tables - {"alembic_version"}  # Exclude Alembic table

        missing_views = reg_views - db_views
        extra_views = db_views - reg_views

        return {
            "missing": list(missing_tables) + list(missing_views),
            "extra": list(extra_tables) + list(extra_views),
            "mismatched": [],  # Would need deeper comparison for this
            "valid": len(missing_tables | missing_views | extra_tables | extra_views) == 0,
        }

    def generate_schema_sql(self) -> str:
        """Generate complete schema DDL in dependency order."""
        sql_statements = []

        for obj in self.get_creation_order():
            if obj.type == ObjectType.TABLE:
                # Tables should be created via SQLAlchemy models
                continue
            elif obj.type == ObjectType.VIEW:
                sql_statements.append(f"-- View: {obj.name}")
                sql_statements.append(f"CREATE VIEW {obj.name} AS {obj.definition};")
                sql_statements.append("")

        return "\n".join(sql_statements)


# Global registry instance
registry = DatabaseRegistry()


def register_views_from_module():
    """Register all views from the views module."""
    from app.db.views import ALL_VIEWS

    for view in ALL_VIEWS:
        obj = DatabaseObject(
            name=view.name,
            type=ObjectType.VIEW,
            definition=view.sqltext,
            dependencies=view.dependencies,
        )
        registry.register(obj)


def register_tables_from_metadata(metadata):
    """Register all tables from SQLAlchemy metadata."""
    for table in metadata.tables.values():
        obj = DatabaseObject(
            name=table.name,
            type=ObjectType.TABLE,
            definition=str(table.compile()),
            metadata={"columns": [col.name for col in table.columns]},
        )
        registry.register(obj)

        # Register indexes
        for index in table.indexes:
            idx_obj = DatabaseObject(
                name=index.name or f"idx_{table.name}_{index.columns}",
                type=ObjectType.INDEX,
                definition=str(index),
                metadata={"table": table.name},
            )
            registry.register(idx_obj)


def discover_from_database(connection):
    """Discover and register objects from live database."""
    inspector = inspect(connection)

    # Discover tables
    for table_name in inspector.get_table_names():
        if table_name == "alembic_version":
            continue

        columns = inspector.get_columns(table_name)
        obj = DatabaseObject(
            name=table_name,
            type=ObjectType.TABLE,
            definition="",  # Would need to reconstruct from columns
            metadata={"columns": [col["name"] for col in columns]},
        )
        registry.register(obj)

    # Discover views
    for view_name in inspector.get_view_names():
        # Get view definition from PostgreSQL
        result = connection.execute(
            text(f"SELECT pg_get_viewdef('{view_name}'::regclass, true)")
        ).scalar()

        obj = DatabaseObject(name=view_name, type=ObjectType.VIEW, definition=result)
        registry.register(obj)
