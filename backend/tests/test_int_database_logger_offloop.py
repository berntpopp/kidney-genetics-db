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
