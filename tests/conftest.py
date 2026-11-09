"""Shared pytest fixtures.

Every test that touches the database gets its own temporary SQLite file, so the
real ``%LOCALAPPDATA%\\GarageManager\\garage_manager.db`` is never used.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

import pytest

import database.connection as connection


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point ``database.connection`` at a fresh, empty DB file.

    The schema is created by the same code path the app uses
    (``get_connection`` -> ``_ensure_schema`` + ``_apply_migrations``).
    """
    db_file = tmp_path / "test_garage.db"
    monkeypatch.setattr(connection, "db_path", db_file)
    with connection.get_connection():
        pass
    yield db_file


@pytest.fixture
def future_date() -> str:
    """An ISO date a few days ahead, valid for new appointments."""
    return (date.today() + timedelta(days=3)).isoformat()


@pytest.fixture
def tz_where_local_date_differs_from_utc(monkeypatch):
    """Switch the process time zone so that local date != UTC date right now.

    Proves dates come from the local clock and not from SQLite's CURRENT_DATE
    (UTC). Needs ``time.tzset``, so it is skipped on Windows.
    """
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is not available on this platform (Windows)")
    utc_hour = datetime.now(timezone.utc).hour
    # POSIX TZ names have inverted signs: "Etc/GMT+12" is UTC-12.
    monkeypatch.setenv("TZ", "Etc/GMT+12" if utc_hour < 12 else "Etc/GMT-14")
    time.tzset()
    assert date.today() != datetime.now(timezone.utc).date()
    yield
    monkeypatch.undo()
    time.tzset()
