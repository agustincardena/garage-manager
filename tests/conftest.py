"""Shared pytest fixtures.

Every test that touches the database gets its own temporary SQLite file, so the
real ``%LOCALAPPDATA%\\GarageManager\\garage_manager.db`` is never used.
"""

from __future__ import annotations

from datetime import date, timedelta

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
