#!/usr/bin/env python
"""Rebuild all data from unified sources."""

import asyncio

from app.pipeline.run import run_update_pipeline


async def rebuild_all():
    """Run the unified pipeline update for all sources."""
    print("🔄 Starting full data rebuild...")

    # Run the pipeline update
    await run_update_pipeline(
        sources=["panelapp", "hpo", "clingen", "gencc", "pubtator"], force=True
    )

    print("✅ Data rebuild complete!")


if __name__ == "__main__":
    asyncio.run(rebuild_all())
