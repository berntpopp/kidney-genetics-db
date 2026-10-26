"""make db-clean must not wipe expert-curated associations through TRUNCATE ... CASCADE (#26)."""

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "clean_database", Path(__file__).resolve().parents[1] / "scripts" / "clean_database.py"
)
clean_database = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(clean_database)


class _Result:
    def __init__(self, row):
        self.row = row

    def first(self):
        return self.row


class _Conn:
    def __init__(self, has_records):
        self.has_records = has_records
        self.sql: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, stmt):
        self.sql.append(str(stmt))
        return _Result((1,) if self.has_records else None)

    def commit(self):
        pass


class _Engine:
    def __init__(self, conn):
        self.conn = conn

    def connect(self):
        return self.conn


@pytest.mark.unit
@pytest.mark.parametrize("has_records", [True, False])
def test_clean_refuses_when_expert_records_exist(monkeypatch, has_records):
    conn = _Conn(has_records)
    monkeypatch.setattr(clean_database, "create_engine", lambda *a, **k: _Engine(conn))

    if has_records:
        with pytest.raises(SystemExit):
            clean_database.clean_database()
        assert not any("TRUNCATE" in s for s in conn.sql)
    else:
        clean_database.clean_database()
        assert any("TRUNCATE TABLE genes" in s for s in conn.sql)
