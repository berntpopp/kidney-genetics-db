"""
Alembic environment configuration with view management support
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import models and settings
# Import all models to ensure they're registered with Base.metadata
# Import custom operations for view management
# This registers the custom operations with Alembic
import app.db.alembic_ops  # noqa: F401
from app.core.config import settings
from app.models import Base

# this is the Alembic Config object
config = context.config

# Set database URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects during autogenerate.
    Exclude views as they are managed separately via ReplaceableObjects.
    """
    # Exclude views from autogenerate
    if type_ == "table" and reflected and hasattr(object, "info"):
        # Check if this is marked as a view
        if object.info.get("is_view", False):
            return False

    # Exclude reflected views
    if type_ == "table" and reflected and compare_to is None:
        # This is a table in the database but not in metadata
        # Could be a view, check the name against known views
        from app.db.views import ALL_VIEWS

        view_names = {view.name for view in ALL_VIEWS}
        if name in view_names:
            return False

    return True


def process_revision_directives(context, revision, directives):
    """Prevent empty migrations from being generated."""
    if config.cmd_opts and getattr(config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops and script.upgrade_ops.is_empty():
            directives[:] = []
            print("No changes detected, skipping migration generation.")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,  # Filter out views
            process_revision_directives=process_revision_directives,
            compare_type=True,  # Enable type comparison
            compare_server_default=True,  # Compare server defaults
            include_schemas=False,  # Single schema for this project
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
