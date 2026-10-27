"""#363: database log writes must not run on the event loop thread."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from app.core.logging.database_logger import DatabaseLogger


@pytest.mark.asyncio
async def test_log_insert_runs_off_the_event_loop_thread():
    threads: list[int] = []
    session = MagicMock()
    session.execute.side_effect = lambda *a, **k: threads.append(threading.get_ident())
    factory = MagicMock(
        return_value=MagicMock(__enter__=lambda s: session, __exit__=lambda *a: None)
    )

    with patch("app.core.database.SessionLocal", factory):
        await DatabaseLogger()._write_log_entry(
            "INFO", "msg", "test", None, None, None, None, None, None
        )

    assert threads and threads[0] != threading.get_ident()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_request_fields_come_from_context_when_no_request_is_passed():
    """#423: request logs arrive via UnifiedLogger without a Request object."""
    session = MagicMock()
    factory = MagicMock(
        return_value=MagicMock(__enter__=lambda s: session, __exit__=lambda *a: None)
    )
    extra = {
        "method": "GET",
        "endpoint": "/api/genes",
        "status_code": 200,
        "processing_time_ms": 12,
    }

    with patch("app.core.database.SessionLocal", factory):
        await DatabaseLogger()._write_log_entry(
            "INFO", "Request completed", "request_middleware", None, None, extra, None, None, None
        )
        await DatabaseLogger()._write_log_entry(
            "INFO", "Pipeline step", "test", None, None, {"source": "x"}, None, None, None
        )
        # Pipeline logs reuse status_code/path for upstream APIs and files
        upstream = {"status_code": 503, "path": "/tmp/x", "processing_time_ms": 9}
        await DatabaseLogger()._write_log_entry(
            "WARNING", "UniProt failed", "uniprot", None, None, upstream, None, None, None
        )

    request_log, other_log, upstream_log = (c.args[1] for c in session.execute.call_args_list)
    assert (request_log["method"], request_log["path"]) == ("GET", "/api/genes")
    assert (request_log["status_code"], request_log["duration_ms"]) == (200, 12)
    assert [other_log[k] for k in ("method", "path", "status_code", "duration_ms")] == [None] * 4
    assert [upstream_log[k] for k in ("path", "status_code", "duration_ms")] == [None] * 3
