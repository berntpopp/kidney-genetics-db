"""#327: every progress commit records when the source last reported progress."""

from datetime import datetime, timezone

from app.core.progress_tracker import ProgressTracker


def test_progress_commit_sets_last_update_at(db_session):
    tracker = ProgressTracker(db_session, "test_last_update_source")
    old = datetime(2000, 1, 1, tzinfo=timezone.utc)
    tracker.progress_record.last_update_at = old
    db_session.flush()

    tracker.update(operation="working", force=True)

    db_session.refresh(tracker.progress_record)
    assert tracker.progress_record.last_update_at > old
    assert tracker.progress_record.to_dict()["last_update_at"] is not None
