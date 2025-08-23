"""
ReplaceableObject pattern for managing database views and functions.
Based on Alembic cookbook best practices.
"""

from dataclasses import dataclass, field


@dataclass
class ReplaceableObject:
    """
    Represents a database object that can be replaced (views, functions, procedures).

    Attributes:
        name: The name of the database object
        sqltext: The SQL definition of the object
        dependencies: List of object names this object depends on
        object_type: Type of object (VIEW, FUNCTION, etc.)
    """

    name: str
    sqltext: str
    dependencies: list[str] = field(default_factory=list)
    object_type: str = "VIEW"

    def create_statement(self) -> str:
        """Generate CREATE statement for this object."""
        if self.object_type == "VIEW":
            return f"CREATE VIEW {self.name} AS {self.sqltext}"
        elif self.object_type == "FUNCTION":
            return f"CREATE FUNCTION {self.name} {self.sqltext}"
        else:
            raise ValueError(f"Unknown object type: {self.object_type}")

    def drop_statement(self) -> str:
        """Generate DROP statement for this object."""
        if self.object_type == "VIEW":
            return f"DROP VIEW IF EXISTS {self.name} CASCADE"
        elif self.object_type == "FUNCTION":
            return f"DROP FUNCTION IF EXISTS {self.name} CASCADE"
        else:
            raise ValueError(f"Unknown object type: {self.object_type}")

    def replace_statement(self) -> str:
        """Generate CREATE OR REPLACE statement for this object."""
        if self.object_type == "VIEW":
            return f"CREATE OR REPLACE VIEW {self.name} AS {self.sqltext}"
        elif self.object_type == "FUNCTION":
            return f"CREATE OR REPLACE FUNCTION {self.name} {self.sqltext}"
        else:
            raise ValueError(f"Unknown object type: {self.object_type}")


def topological_sort(objects: list[ReplaceableObject]) -> list[ReplaceableObject]:
    """
    Sort ReplaceableObjects in dependency order using topological sort.

    Args:
        objects: List of ReplaceableObject instances

    Returns:
        List of objects sorted so dependencies come before dependents
    """
    # Create a mapping of name to object
    obj_map = {obj.name: obj for obj in objects}

    # Track visited and currently visiting nodes
    visited = set()
    visiting = set()
    sorted_objects = []

    def visit(obj_name: str):
        if obj_name in visited:
            return
        if obj_name in visiting:
            raise ValueError(f"Circular dependency detected involving {obj_name}")

        if obj_name not in obj_map:
            # Dependency not in our list, skip it
            return

        visiting.add(obj_name)
        obj = obj_map[obj_name]

        # Visit dependencies first
        for dep in obj.dependencies:
            visit(dep)

        visiting.remove(obj_name)
        visited.add(obj_name)
        sorted_objects.append(obj)

    # Visit all objects
    for obj_name in obj_map:
        visit(obj_name)

    return sorted_objects
