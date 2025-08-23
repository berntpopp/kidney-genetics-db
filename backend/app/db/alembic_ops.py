"""
Custom Alembic operations for managing views and other replaceable database objects.
Based on Alembic cookbook best practices.
"""

from alembic.operations import MigrateOperation, Operations
from app.db.replaceable_objects import ReplaceableObject


class ReversibleOp(MigrateOperation):
    """Base class for reversible database operations."""

    def __init__(self, target: ReplaceableObject):
        self.target = target

    @classmethod
    def invoke_for_target(cls, operations, target):
        """Create and invoke this operation for a target object."""
        op = cls(target)
        return operations.invoke(op)

    def reverse(self):
        """Return the reverse operation."""
        raise NotImplementedError()

    @classmethod
    def replace(cls, operations, target, replaces=None, replace_with=None):
        """Replace an object by dropping old and creating new."""
        if replaces:
            # Replacing old version with new version
            old_obj = cls._get_object_from_version(operations, replaces)
            drop_old = cls(old_obj).reverse()
            create_new = cls(target)
        elif replace_with:
            # Reverting to old version
            old_obj = cls._get_object_from_version(operations, replace_with)
            drop_old = cls(target).reverse()
            create_new = cls(old_obj)
        else:
            raise TypeError("Either 'replaces' or 'replace_with' is required")

        operations.invoke(drop_old)
        operations.invoke(create_new)

    @classmethod
    def _get_object_from_version(cls, operations, ident):
        """Get an object definition from a specific migration version."""
        version, objname = ident.split(".")
        module = operations.get_context().script.get_revision(version).module
        obj = getattr(module, objname)
        return obj


# VIEW OPERATIONS


@Operations.register_operation("create_view", "invoke_for_target")
@Operations.register_operation("replace_view", "replace")
class CreateViewOp(ReversibleOp):
    """Operation to create a database view."""

    def reverse(self):
        return DropViewOp(self.target)


@Operations.register_operation("drop_view", "invoke_for_target")
class DropViewOp(ReversibleOp):
    """Operation to drop a database view."""

    def reverse(self):
        return CreateViewOp(self.target)


# FUNCTION OPERATIONS


@Operations.register_operation("create_function", "invoke_for_target")
@Operations.register_operation("replace_function", "replace")
class CreateFunctionOp(ReversibleOp):
    """Operation to create a database function."""

    def reverse(self):
        return DropFunctionOp(self.target)


@Operations.register_operation("drop_function", "invoke_for_target")
class DropFunctionOp(ReversibleOp):
    """Operation to drop a database function."""

    def reverse(self):
        return CreateFunctionOp(self.target)


# Implementation functions for the operations


@Operations.implementation_for(CreateViewOp)
def create_view(operations, operation):
    """Execute CREATE VIEW statement."""
    operations.execute(operation.target.create_statement())


@Operations.implementation_for(DropViewOp)
def drop_view(operations, operation):
    """Execute DROP VIEW statement."""
    operations.execute(operation.target.drop_statement())


@Operations.implementation_for(CreateFunctionOp)
def create_function(operations, operation):
    """Execute CREATE FUNCTION statement."""
    operations.execute(operation.target.create_statement())


@Operations.implementation_for(DropFunctionOp)
def drop_function(operations, operation):
    """Execute DROP FUNCTION statement."""
    operations.execute(operation.target.drop_statement())


# Helper functions for use in migrations


def create_all_views(op, views):
    """
    Create multiple views in dependency order.

    Args:
        op: The Alembic operations object
        views: List of ReplaceableObject instances
    """
    from app.db.replaceable_objects import topological_sort

    sorted_views = topological_sort(views)
    for view in sorted_views:
        op.create_view(view)


def drop_all_views(op, views):
    """
    Drop multiple views in reverse dependency order.

    Args:
        op: The Alembic operations object
        views: List of ReplaceableObject instances
    """
    from app.db.replaceable_objects import topological_sort

    sorted_views = topological_sort(views)
    # Drop in reverse order to respect dependencies
    for view in reversed(sorted_views):
        op.drop_view(view)
