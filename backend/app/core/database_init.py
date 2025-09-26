"""
Database initialization module for automatic setup on startup.

This module handles all database initialization tasks including:
- Creating missing tables and views
- Setting up default admin user
- Running evidence aggregation
- Clearing corrupted cache
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.models.cache import CacheEntry
from app.models.user import User
from app.pipeline.aggregate import update_all_curations

logger = get_logger(__name__)


async def initialize_database(db: Session) -> dict:
    """
    Complete database initialization routine.

    This function performs all necessary initialization steps to ensure
    the database is in a working state after a reset or fresh start.

    Args:
        db: Database session

    Returns:
        dict: Status of initialization steps
    """
    status = {
        "views_created": False,
        "admin_created": False,
        "cache_cleared": False,
        "aggregation_completed": False,
        "errors": [],
    }

    try:
        # Step 1: Create missing views
        await logger.info("Checking and creating database views...")
        await create_database_views(db)
        status["views_created"] = True
        await logger.info("Database views created successfully")

        # Step 2: Create default admin user if not exists
        await logger.info("Checking admin user...")
        admin_created = await create_default_admin(db)
        status["admin_created"] = admin_created
        if admin_created:
            await logger.info("Admin user created successfully")
        else:
            await logger.info("Admin user already exists")

        # Step 3: Clear corrupted cache
        await logger.info("Clearing cache...")
        cache_cleared = await clear_cache(db)
        status["cache_cleared"] = cache_cleared
        await logger.info(f"Cache cleared: {cache_cleared} entries removed")

        # Step 4: Check if we need to run evidence aggregation
        await logger.info("Checking if evidence aggregation is needed...")
        aggregation_needed = await check_aggregation_needed(db)

        if aggregation_needed:
            await logger.info("Running evidence aggregation...")
            # Run aggregation in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, update_all_curations, db)
            status["aggregation_completed"] = True
            await logger.info(
                f"Evidence aggregation completed: {result.get('curations_created', 0)} curations created"
            )
        else:
            await logger.info("Evidence aggregation not needed")

    except Exception as e:
        await logger.error(f"Error during database initialization: {str(e)}")
        status["errors"].append(str(e))

    return status


async def create_database_views(db: Session) -> None:
    """
    Create all required database views using the proper definitions.

    Args:
        db: Database session
    """
    try:
        from app.db.views import ALL_VIEWS

        # Check which views already exist
        result = db.execute(
            text("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'public'
        """)
        )
        existing_views = {row[0] for row in result.fetchall()}

        # Create missing views in dependency order
        created_count = 0
        for view_def in ALL_VIEWS:
            if view_def.name not in existing_views:
                try:
                    db.execute(text(f"CREATE VIEW {view_def.name} AS {view_def.sqltext}"))
                    created_count += 1
                    await logger.info(f"Created view: {view_def.name}")
                except Exception as e:
                    # Log but don't fail - view might have different definition
                    await logger.warning(f"Could not create view {view_def.name}: {str(e)}")

        if created_count > 0:
            db.commit()
            await logger.info(f"Created {created_count} missing views")
        else:
            await logger.info("All required views already exist")

        # Check for and create gene_annotations_summary materialized view separately
        # This is a materialized view, not a regular view
        result = db.execute(
            text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_matviews
                WHERE matviewname = 'gene_annotations_summary'
            )
        """)
        )
        has_summary = result.scalar()

        if not has_summary:
            db.execute(
                text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS gene_annotations_summary AS
                SELECT
                    g.id as gene_id,
                    g.approved_symbol,
                    g.hgnc_id,
                    ga_hgnc.annotations->>'ncbi_gene_id' as ncbi_gene_id,
                    ga_hgnc.annotations->>'ensembl_gene_id' as ensembl_gene_id,
                    ga_hgnc.annotations->>'mane_select' as mane_select_transcript,
                    (ga_gnomad.annotations->>'pLI')::float as pli,
                    (ga_gnomad.annotations->>'oe_lof')::float as oe_lof,
                    (ga_gnomad.annotations->>'oe_lof_upper')::float as oe_lof_upper,
                    (ga_gnomad.annotations->>'oe_lof_lower')::float as oe_lof_lower,
                    (ga_gnomad.annotations->>'lof_z')::float as lof_z,
                    (ga_gnomad.annotations->>'mis_z')::float as mis_z,
                    (ga_gnomad.annotations->>'syn_z')::float as syn_z,
                    (ga_gnomad.annotations->>'oe_mis')::float as oe_mis,
                    (ga_gnomad.annotations->>'oe_syn')::float as oe_syn
                FROM genes g
                LEFT JOIN gene_annotations ga_hgnc ON g.id = ga_hgnc.gene_id AND ga_hgnc.source = 'hgnc'
                LEFT JOIN gene_annotations ga_gnomad ON g.id = ga_gnomad.gene_id AND ga_gnomad.source = 'gnomad'
            """)
            )
            db.commit()
            await logger.info("Created gene_annotations_summary materialized view")

    except Exception as e:
        await logger.error(f"Error creating database views: {str(e)}")
        # Don't raise - allow startup to continue


async def create_default_admin(db: Session) -> bool:
    """
    Create default admin user if it doesn't exist.

    Args:
        db: Database session

    Returns:
        bool: True if admin was created, False if already existed
    """
    from app.core.config import settings

    try:
        # Check if admin exists
        admin = db.query(User).filter(User.username == settings.ADMIN_USERNAME).first()

        if not admin:
            # Create admin user using config values
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                username=settings.ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                full_name="Administrator",
                role="admin",
                is_active=True,
                is_verified=True,
                is_admin=True,
            )

            db.add(admin_user)
            db.commit()

            await logger.info(
                f"Created default admin user (username: {settings.ADMIN_USERNAME}, password: from config)"
            )
            return True
        else:
            # Ensure admin has correct role and is active
            if admin.role != "admin" or not admin.is_active:
                admin.role = "admin"
                admin.is_active = True
                admin.is_verified = True
                admin.is_admin = True
                db.commit()
                await logger.info("Updated existing admin user settings")
            return False

    except Exception as e:
        await logger.error(f"Error creating admin user: {str(e)}")
        db.rollback()
        return False


async def clear_cache(db: Session) -> int:
    """
    Clear all cache entries to avoid deserialization errors.

    Args:
        db: Database session

    Returns:
        int: Number of cache entries cleared
    """
    try:
        # Count existing cache entries
        count = db.query(CacheEntry).count()

        if count > 0:
            # Clear all cache
            db.query(CacheEntry).delete()
            db.commit()
            await logger.info(f"Cleared {count} cache entries")
            return count
        return 0

    except Exception as e:
        await logger.error(f"Error clearing cache: {str(e)}")
        db.rollback()
        return 0


async def check_aggregation_needed(db: Session) -> bool:
    """
    Check if evidence aggregation needs to be run.

    Args:
        db: Database session

    Returns:
        bool: True if aggregation is needed
    """
    try:
        # Check if we have genes but no curations
        genes_count = db.execute(text("SELECT COUNT(*) FROM genes")).scalar()
        curations_count = db.execute(text("SELECT COUNT(*) FROM gene_curations")).scalar()

        # Need aggregation if we have genes but no curations
        return genes_count > 0 and curations_count == 0

    except Exception as e:
        await logger.error(f"Error checking aggregation status: {str(e)}")
        return False


async def verify_database_ready(db: Session) -> dict:
    """
    Verify that the database is ready for use.

    Args:
        db: Database session

    Returns:
        dict: Verification status
    """
    status = {
        "ready": True,
        "genes_count": 0,
        "curations_count": 0,
        "admin_exists": False,
        "views_exist": False,
    }

    try:
        # Check genes
        status["genes_count"] = db.execute(text("SELECT COUNT(*) FROM genes")).scalar() or 0

        # Check curations
        status["curations_count"] = (
            db.execute(text("SELECT COUNT(*) FROM gene_curations")).scalar() or 0
        )

        # Check admin
        admin = db.query(User).filter(User.username == "admin").first()
        status["admin_exists"] = admin is not None

        # Check views
        result = db.execute(
            text("""
            SELECT COUNT(*) FROM information_schema.views
            WHERE table_name IN ('gene_scores')
        """)
        )
        status["views_exist"] = result.scalar() > 0

        # Determine if ready
        status["ready"] = status["views_exist"] and status["admin_exists"]

        if not status["ready"]:
            reasons = []
            if not status["views_exist"]:
                reasons.append("Missing database views")
            if not status["admin_exists"]:
                reasons.append("No admin user")
            status["reason"] = ", ".join(reasons)

    except Exception as e:
        status["ready"] = False
        status["error"] = str(e)

    return status
