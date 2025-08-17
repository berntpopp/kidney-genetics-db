"""
CLI for running pipeline updates
"""

import logging
import sys
from datetime import datetime, timezone

import click
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.gene import PipelineRun
from app.pipeline.aggregate import update_all_curations
from app.pipeline.sources.clingen import update_clingen_data
from app.pipeline.sources.gencc import update_gencc_data
# HPO now uses async version in background_tasks.py - not available for sync CLI
from app.pipeline.sources.panelapp import update_all_panelapp
from app.pipeline.sources.pubtator import update_pubtator_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Kidney Genetics Pipeline CLI"""
    pass


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["all", "panelapp", "hpo", "pubtator", "clingen", "gencc"]),
    default="all",
    help="Which data source to update",
)
def update(source: str):
    """Update gene data from external sources"""
    logger.info(f"Starting pipeline update for source: {source}")

    # Get database session
    db: Session = next(get_db())

    # Create pipeline run record
    run = PipelineRun(
        status="running",
        started_at=datetime.now(timezone.utc),
        stats={},
    )
    db.add(run)
    db.commit()

    try:
        all_stats = []

        if source in ["all", "panelapp"]:
            logger.info("Updating PanelApp data...")
            stats = update_all_panelapp(db)
            all_stats.append(stats)

        if source in ["all", "hpo"]:
            logger.info("HPO update not available in sync CLI - use API endpoint instead")
            # HPO now uses async implementation - see background_tasks.py
            # stats = update_hpo_data(db)
            # all_stats.append(stats)

        if source in ["all", "pubtator"]:
            logger.info("Updating PubTator data...")
            stats = update_pubtator_data(db)
            all_stats.append(stats)

        if source in ["all", "clingen"]:
            logger.info("Updating ClinGen data...")
            stats = update_clingen_data(db)
            all_stats.append(stats)

        if source in ["all", "gencc"]:
            logger.info("Updating GenCC data...")
            stats = update_gencc_data(db)
            all_stats.append(stats)

        # Always update curations after source updates
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

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_log = str(e)
        db.add(run)
        db.commit()
        raise

    finally:
        db.close()


@cli.command()
def list_runs():
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
