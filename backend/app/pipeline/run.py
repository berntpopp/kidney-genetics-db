"""
CLI for running pipeline updates - Now using AsyncClick for native async support
"""

from datetime import datetime, timezone

import asyncclick as click
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import configure_logging, get_logger
from app.core.progress_tracker import ProgressTracker
from app.models.gene import PipelineRun
from app.pipeline.aggregate import update_all_curations
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource

# Configure unified logging for CLI
configure_logging(log_level="INFO", database_enabled=True, console_enabled=True)

logger = get_logger(__name__)


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
    await logger.info("Starting pipeline update", source=source)

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

        # The unified sources handle async internally even with sync session
        if source in ["all", "panelapp"]:
            await logger.info("Updating PanelApp data")
            # Create tracker specific to this source
            tracker = ProgressTracker(db=db, source_name="PanelApp")
            source_obj = PanelAppUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            await logger.info("PanelApp update complete", stats=stats)

        if source in ["all", "hpo"]:
            await logger.info("Updating HPO data")
            # Create tracker specific to this source
            tracker = ProgressTracker(db=db, source_name="HPO")
            source_obj = HPOUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            await logger.info("HPO update complete", stats=stats)

        if source in ["all", "pubtator"]:
            await logger.info("Updating PubTator data")
            # Create tracker specific to this source
            tracker = ProgressTracker(db=db, source_name="PubTator")
            source_obj = PubTatorUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            await logger.info("PubTator update complete", stats=stats)

        if source in ["all", "clingen"]:
            await logger.info("Updating ClinGen data")
            # Create tracker specific to this source
            tracker = ProgressTracker(db=db, source_name="ClinGen")
            source_obj = ClinGenUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            await logger.info("ClinGen update complete", stats=stats)

        if source in ["all", "gencc"]:
            await logger.info("Updating GenCC data")
            # Create tracker specific to this source
            tracker = ProgressTracker(db=db, source_name="GenCC")
            source_obj = GenCCUnifiedSource(db_session=db)
            stats = await source_obj.update_data(db, tracker)
            all_stats.append(stats)
            await logger.info("GenCC update complete", stats=stats)

        # Update curations after source updates
        if all_stats:
            await logger.info("Updating gene curations and scores")
            curation_stats = update_all_curations(db)
            all_stats.append(curation_stats)

        # Update pipeline run with results
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.stats = {"sources": all_stats}
        db.add(run)
        db.commit()

        await logger.info("Pipeline update completed successfully", sources_updated=len(all_stats))

    except Exception as e:
        await logger.error("Pipeline error", error=e)
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
