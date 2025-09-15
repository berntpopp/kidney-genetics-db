#!/usr/bin/env python
"""Rebuild all data from unified sources."""

import asyncio
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource
from app.pipeline.run import run_update_pipeline

async def rebuild_all():
    """Run the unified pipeline update for all sources."""
    print("🔄 Starting full data rebuild...")

    # Run the pipeline update
    await run_update_pipeline(
        sources=["panelapp", "hpo", "clingen", "gencc", "pubtator"],
        force=True
    )

    print("✅ Data rebuild complete!")

if __name__ == "__main__":
    asyncio.run(rebuild_all())