#!/usr/bin/env python
"""Run all unified data sources from scratch."""

import asyncio

from app.core.database import SessionLocal
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource
from app.pipeline.sources.unified.panelapp import PanelAppUnifiedSource
from app.pipeline.sources.unified.pubtator import PubTatorUnifiedSource


async def run_all_sources():
    db = SessionLocal()
    try:
        sources = [
            ("PanelApp", PanelAppUnifiedSource),
            ("HPO", HPOUnifiedSource),
            ("ClinGen", ClinGenUnifiedSource),
            ("GenCC", GenCCUnifiedSource),
            ("PubTator", PubTatorUnifiedSource),
        ]

        for name, SourceClass in sources:
            print(f"\n📦 Starting {name}...")
            try:
                source = SourceClass(db)
                await source.update(force=True)
                print(f"✅ Completed {name}")
            except Exception as e:
                print(f"❌ Error in {name}: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_all_sources())
