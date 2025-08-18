"""
CLI for running pipeline updates - Now using AsyncClick for native async support
"""

import logging
import sys
from datetime import datetime, timezone

import asyncclick as click
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.progress_tracker import ProgressTracker
from app.models.gene import PipelineRun
from app.pipeline.aggregate import update_all_curations
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@click.group()
async def cli():
    """Kidney Genetics Pipeline CLI - Async version"""
    pass


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["all", "panelapp", "hpo", "pubtator", "clingen", "gencc"]),
    default="all",
    help="Which data source to update",
)
async def update(source: str):
    """Update gene data from external sources - now fully async"""
    logger.info(f"Starting pipeline update for source: {source}")

    # Get database session - unified sources work with both sync and async
    db: Session = next(get_db())
    
    try:
        # Create pipeline run record
        run = PipelineRun(
            status="running",
            started_at=datetime.now(timezone.utc),
            stats={},
        )
        db.add(run)
        db.commit()

        all_stats = []
        tracker = ProgressTracker(source_name=source)

        # The unified sources handle async internally even with sync session
        if source in ["all", "panelapp"]:
            logger.info("Updating PanelApp data...")
            source_obj = PanelAppUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            logger.info(f"PanelApp update complete: {stats}")

        if source in ["all", "hpo"]:
            logger.info("Updating HPO data...")
            source_obj = HPOUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            logger.info(f"HPO update complete: {stats}")

        if source in ["all", "pubtator"]:
            logger.info("Updating PubTator data...")
            source_obj = PubTatorUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            logger.info(f"PubTator update complete: {stats}")

        if source in ["all", "clingen"]:
            logger.info("Updating ClinGen data...")
            source_obj = ClinGenUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            logger.info(f"ClinGen update complete: {stats}")

        if source in ["all", "gencc"]:
            logger.info("Updating GenCC data...")
            source_obj = GenCCUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            logger.info(f"GenCC update complete: {stats}")

        # Update curations after source updates
        if all_stats:
            logger.info("Updating gene curations and scores...")
            curation_stats = update_all_curations(db)
            all_stats.append(curation_stats)

        # Update pipeline run with results
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.stats = {"sources": all_stats}
        db.add(run)
        db.commit()

        logger.info("Pipeline update completed successfully")
        logger.info(f"Summary: {len(all_stats)} sources updated")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_log = str(e)
        db.add(run)
        db.commit()
        raise
    finally:
        db.close()


@cli.command()
async def list_runs():
    """List recent pipeline runs"""
    db: Session = next(get_db())
    
    try:
        runs = db.query(PipelineRun).order_by(PipelineRun.id.desc()).limit(10).all()

        if not runs:
            click.echo("No pipeline runs found")
            return

        click.echo("Recent pipeline runs:")
        click.echo("-" * 60)

        for run in runs:
            started = run.started_at.isoformat() if run.started_at else "N/A"
            completed = run.completed_at.isoformat() if run.completed_at else "N/A"

            click.echo(f"ID: {run.id}")
            click.echo(f"Status: {run.status}")
            click.echo(f"Started: {started}")
            click.echo(f"Completed: {completed}")
            if run.error_log:
                click.echo(f"Error: {run.error_log[:100]}...")
            click.echo("-" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    cli()
