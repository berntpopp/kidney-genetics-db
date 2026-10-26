"""A progress write must not leave its session idle in a transaction (#249/#370).

Seen live: the post-commit reload for the broadcast opened a read that idled until the next
heartbeat; PostgreSQL's 30 s idle-in-transaction timeout killed the pipeline's connection.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.progress_tracker import ProgressTracker


@pytest.mark.asyncio
async def test_progress_write_leaves_no_open_transaction(test_engine):
    name = f"int_idle_{uuid.uuid4().hex[:6]}"
    session = sessionmaker(bind=test_engine)()  # real commits, like the pipeline's session
    try:
        tracker = ProgressTracker(session, name)
        tracker.start("probe")
        for i in range(3):
            tracker.update(current_item=i, total_items=3, operation=f"step {i}", force=True)
            assert not session.in_transaction()
    finally:
        session.close()
        with test_engine.begin() as conn:
            conn.execute(
                text("DELETE FROM data_source_progress WHERE source_name = :n"), {"n": name}
            )
