"""Versioned migrations (database/migrations.py) and one-time initialization."""

from __future__ import annotations

import logging
import sqlite3
import sys

import pytest

import database.connection as connection
from database import migrations
from tests.helpers import legacy_schema_sql, strip_appointment_order_link


def _version(path) -> int:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()


def _indexes(path) -> set[str]:
    conn = sqlite3.connect(path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    finally:
        conn.close()


def _legacy_db(path, plates=("AA111AA",)) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(legacy_schema_sql())
    conn.execute("INSERT INTO clients (name) VALUES ('Ana')")
    for plate in plates:
        conn.execute("INSERT INTO vehicles (client_id, plate) VALUES (1, ?)", (plate,))
    conn.execute("INSERT INTO orders (vehicle_id, status_id) VALUES (1, 3)")
    conn.execute(
        "INSERT INTO appointments (client_id, vehicle_id, appointment_date, appointment_time,"
        " duration_minutes) VALUES (1, 1, '2030-01-01', '09:00', 90)"
    )
    conn.commit()
    conn.close()


def test_new_database_is_created_at_latest_version(tmp_path):
    db = tmp_path / "new.db"
    assert connection.init_database(db) == migrations.LATEST_VERSION
    assert _version(db) == migrations.LATEST_VERSION
    assert "idx_vehicles_plate_normalized" in _indexes(db)


def test_original_database_is_upgraded_and_keeps_its_data(tmp_path):
    db = tmp_path / "legacy.db"
    _legacy_db(db, plates=(" aa111aa ", "bb222bb"))
    assert _version(db) == 0

    assert connection.init_database(db) == migrations.LATEST_VERSION

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    order_cols = {r[1] for r in conn.execute("PRAGMA table_info(orders)")}
    appt_cols = {r[1] for r in conn.execute("PRAGMA table_info(appointments)")}
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    plates = [r[0] for r in conn.execute("SELECT plate FROM vehicles ORDER BY id")]
    status = conn.execute("SELECT status_id FROM orders").fetchone()[0]
    appts = conn.execute("SELECT COUNT(*) FROM appointments").fetchone()[0]
    conn.close()

    assert {"parts_cost", "customer_charge", "completion_notes"} <= order_cols
    assert "duration_minutes" not in appt_cols
    assert {"incomes", "settings"} <= tables
    assert plates == ["AA111AA", "BB222BB"]  # v2 normalizes plates
    assert status == 1  # removed status 3 -> pending
    assert appts == 1
    assert "idx_vehicles_plate_normalized" in _indexes(db)
    assert "order_id" in appt_cols  # v3


def test_duplicate_plates_skip_the_index_without_blocking(tmp_path, caplog):
    db = tmp_path / "dups.db"
    _legacy_db(db, plates=("AA111AA", "aa111aa"))
    with caplog.at_level(logging.WARNING, logger="database.migrations"):
        assert connection.init_database(db) == migrations.LATEST_VERSION
    assert "idx_vehicles_plate_normalized" not in _indexes(db)
    assert "AA111AA" in caplog.text


def test_migrations_run_only_once(tmp_path, monkeypatch):
    db = tmp_path / "once.db"
    _legacy_db(db)
    connection.init_database(db)

    calls = []
    monkeypatch.setattr(
        migrations, "MIGRATIONS", [(v, lambda c, v=v: calls.append(v)) for v, _ in migrations.MIGRATIONS]
    )
    connection.init_database(db)
    assert calls == []


def test_get_connection_initializes_each_database_once(tmp_path, monkeypatch):
    db = tmp_path / "lazy.db"
    monkeypatch.setattr(connection, "db_path", db)
    calls = []
    real = connection.migrate
    monkeypatch.setattr(connection, "migrate", lambda c, p: calls.append(1) or real(c, p))
    for _ in range(3):
        with connection.get_connection() as conn:
            conn.execute("SELECT COUNT(*) FROM clients").fetchone()
    assert calls == [1]


def test_failed_migration_rolls_back_and_keeps_version(tmp_path, monkeypatch):
    db = tmp_path / "fail.db"
    connection.init_database(db)  # latest version

    def broken(conn):
        conn.execute("CREATE TABLE half_done (id INTEGER)")
        raise RuntimeError("boom")

    latest = migrations.LATEST_VERSION
    monkeypatch.setattr(migrations, "MIGRATIONS", [*migrations.MIGRATIONS, (latest + 1, broken)])
    monkeypatch.setattr(migrations, "LATEST_VERSION", latest + 1)
    with pytest.raises(RuntimeError, match="boom"):
        connection.init_database(db)

    assert _version(db) == latest
    conn = sqlite3.connect(db)
    assert conn.execute(
        "SELECT 1 FROM sqlite_master WHERE name = 'half_done'"
    ).fetchone() is None
    conn.close()


def test_database_from_newer_app_is_refused(tmp_path):
    db = tmp_path / "future.db"
    connection.init_database(db)
    conn = sqlite3.connect(db)
    conn.execute(f"PRAGMA user_version = {migrations.LATEST_VERSION + 1}")
    conn.close()
    with pytest.raises(migrations.DatabaseTooNewError):
        connection.init_database(db)


def test_importing_connection_creates_no_folders(tmp_path):
    """A6: importing the module must not touch the disk (checked in a fresh
    process so this test changes no global state)."""
    import os
    import subprocess
    from pathlib import Path

    repo_root = Path(connection.__file__).resolve().parent.parent
    env = {**os.environ, "LOCALAPPDATA": str(tmp_path / "appdata")}
    out = subprocess.run(
        [sys.executable, "-c", "import database.connection as c; print(c.db_path)"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert Path(out.stdout.strip()) == tmp_path / "appdata" / "GarageManager" / "garage_manager.db"
    assert not (tmp_path / "appdata").exists()


def test_phase1_database_upgrades_cleanly(tmp_path):
    """The database the app created until phase 1: current tables, version 0,
    no normalized-plate index."""
    db = tmp_path / "phase1.db"
    sql = connection.schema_path.read_text(encoding="utf-8")
    sql = strip_appointment_order_link(sql[: sql.index("-- PLATES")])
    conn = sqlite3.connect(db)
    conn.executescript(sql)
    conn.execute("INSERT INTO clients (name) VALUES ('Ana')")
    conn.execute("INSERT INTO vehicles (client_id, plate) VALUES (1, 'AA111AA')")
    conn.execute("INSERT INTO settings (key, value) VALUES ('appointments.slot_capacity', '3')")
    conn.execute("INSERT INTO orders (vehicle_id, status_id, customer_charge) VALUES (1, 5, 100)")
    conn.commit()
    conn.close()

    assert connection.init_database(db) == migrations.LATEST_VERSION

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT value FROM settings").fetchone()[0] == "3"
    assert conn.execute("SELECT status_id, customer_charge FROM orders").fetchone() == (5, 100)
    conn.close()
    assert "idx_vehicles_plate_normalized" in _indexes(db)
