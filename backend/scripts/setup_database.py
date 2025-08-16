#!/usr/bin/env python3
"""
Comprehensive Database Setup Script

This script ensures all necessary database tables, views, indexes, and initial data
are properly set up following best practices. Can be run on a fresh database or
used to repair/update an existing one.
"""

import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import engine, get_db
from app.models.base import Base
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_all_tables():
    """Create all tables defined in models"""
    logger.info("Creating all database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        raise


def create_views():
    """Create all necessary database views"""
    logger.info("Creating database views...")
    
    views = {
        "gene_scores": """
        CREATE OR REPLACE VIEW gene_scores AS
        SELECT 
            g.id as gene_id,
            g.approved_symbol,
            COUNT(DISTINCT ge.source_name) as source_count,
            COUNT(ge.id) as evidence_count,
            COALESCE(gc.evidence_score, 0) as raw_score,
            COALESCE(gc.evidence_score, 0) as percentage_score,
            (SELECT COUNT(DISTINCT source_name) FROM gene_evidence) as total_active_sources,
            COALESCE(gc.constraint_scores, '{}'::jsonb) as source_percentiles
        FROM genes g
        LEFT JOIN gene_evidence ge ON g.id = ge.gene_id
        LEFT JOIN gene_curations gc ON g.id = gc.gene_id
        GROUP BY g.id, g.approved_symbol, gc.evidence_score, gc.constraint_scores
        ORDER BY g.approved_symbol;
        """
    }
    
    try:
        with engine.connect() as conn:
            for view_name, view_sql in views.items():
                logger.info(f"Creating view: {view_name}")
                conn.execute(text(view_sql))
                conn.commit()
        logger.info("✅ All views created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating views: {e}")
        raise


def create_indexes():
    """Create performance indexes"""
    logger.info("Creating database indexes...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_genes_hgnc_id ON genes(hgnc_id);",
        "CREATE INDEX IF NOT EXISTS idx_genes_approved_symbol ON genes(approved_symbol);",
        "CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene_id ON gene_evidence(gene_id);",
        "CREATE INDEX IF NOT EXISTS idx_gene_evidence_source_name ON gene_evidence(source_name);",
        "CREATE INDEX IF NOT EXISTS idx_gene_curations_gene_id ON gene_curations(gene_id);",
        "CREATE INDEX IF NOT EXISTS idx_gene_normalization_staging_status ON gene_normalization_staging(status);",
        "CREATE INDEX IF NOT EXISTS idx_gene_normalization_staging_source ON gene_normalization_staging(source_name);",
        "CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene_symbol ON gene_evidence(gene_symbol);",
        "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_source ON pipeline_runs(source);",
        "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);",
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                logger.info(f"Creating index...")
                conn.execute(text(index_sql))
                conn.commit()
        logger.info("✅ All indexes created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        raise


def verify_database_integrity():
    """Verify database integrity and report status"""
    logger.info("Verifying database integrity...")
    
    try:
        with engine.connect() as conn:
            # Check table counts
            tables = {
                "genes": "SELECT COUNT(*) FROM genes",
                "gene_evidence": "SELECT COUNT(*) FROM gene_evidence", 
                "gene_curations": "SELECT COUNT(*) FROM gene_curations",
                "gene_normalization_staging": "SELECT COUNT(*) FROM gene_normalization_staging",
                "pipeline_runs": "SELECT COUNT(*) FROM pipeline_runs"
            }
            
            logger.info("📊 Database Status:")
            for table_name, query in tables.items():
                try:
                    result = conn.execute(text(query)).scalar()
                    logger.info(f"  {table_name}: {result} records")
                except Exception as e:
                    logger.warning(f"  {table_name}: Table not accessible ({e})")
            
            # Check views
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM gene_scores")).scalar()
                logger.info(f"  gene_scores view: {result} records")
            except Exception as e:
                logger.warning(f"  gene_scores view: Not accessible ({e})")
            
            # Check HGNC coverage
            try:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN hgnc_id IS NOT NULL THEN 1 END) as with_hgnc,
                        ROUND(COUNT(CASE WHEN hgnc_id IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as coverage
                    FROM genes
                """)).fetchone()
                logger.info(f"  HGNC Coverage: {result[1]}/{result[0]} ({result[2]}%)")
            except Exception as e:
                logger.warning(f"  HGNC Coverage: Cannot calculate ({e})")
                
        logger.info("✅ Database verification completed")
        
    except Exception as e:
        logger.error(f"❌ Error verifying database: {e}")
        raise


def setup_database(skip_aggregation=False):
    """
    Complete database setup process
    
    Args:
        skip_aggregation: If True, skip running gene aggregation (for fresh setups)
    """
    logger.info("🚀 Starting comprehensive database setup...")
    
    try:
        # Step 1: Create all tables
        create_all_tables()
        
        # Step 2: Create views
        create_views()
        
        # Step 3: Create indexes
        create_indexes()
        
        # Step 4: Run gene aggregation if data exists
        if not skip_aggregation:
            logger.info("Running gene curation aggregation...")
            try:
                from app.pipeline.aggregate import update_all_curations
                db = next(get_db())
                try:
                    result = update_all_curations(db)
                    logger.info(f"✅ Gene aggregation completed: {result.get('genes_processed', 0)} genes processed")
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"⚠️  Gene aggregation skipped: {e}")
        
        # Step 5: Verify everything is working
        verify_database_integrity()
        
        logger.info("🎉 Database setup completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"💥 Database setup failed: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup kidney-genetics database")
    parser.add_argument(
        "--skip-aggregation", 
        action="store_true", 
        help="Skip gene aggregation step (for fresh databases)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify database status, don't create anything"
    )
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_database_integrity()
    else:
        success = setup_database(skip_aggregation=args.skip_aggregation)
        sys.exit(0 if success else 1)