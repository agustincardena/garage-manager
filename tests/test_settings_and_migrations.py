"""Settings (slot capacity), the transaction helper and phase 1 migrations."""

from __future__ import annotations

import sqlite3

import pytest

import database.connection as connection
from services.client_service import ClientService
from tests.helpers import legacy_schema_sql
from services.settings_service import (
    DEFAULT_SLOT_CAPACITY,
    MAX_SLOT_CAPACITY,
    SettingsService,
)


def test_slot_capacity_defaults_to_one_and_persists(isolated_db):
    settings = SettingsService()
    assert settings.get_slot_capacity() == DEFAULT_SLOT_CAPACITY == 1
    settings.set_slot_capacity(3)
    assert SettingsService().get_slot_capacity() == 3
    settings.set_slot_capacity("4")
    assert settings.get_slot_capacity() == 4


@pytest.mark.parametrize("value", [0, -1, MAX_SLOT_CAPACITY + 1, "dos", None])
def test_slot_capacity_rejects_invalid_values(isolated_db, value):
    with pytest.raises(ValueError, match="errors.settings.slot_capacity_range"):
        SettingsService().set_slot_capacity(value)
    assert SettingsService().get_slot_capacity() == 1


def test_corrupt_stored_capacity_falls_back_to_default(isolated_db):
    with connection.get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES ('appointments.slot_capacity', 'x')"
        )
        conn.commit()
    assert SettingsService().get_slot_capacity() == 1


def test_transaction_rolls_back_every_step_on_error(isolated_db):
    clients = ClientService()
    with pytest.raises(RuntimeError):
        with connection.transaction() as conn:
            clients.create_client("Uno", conn=conn)
            clients.create_client("Dos", conn=conn)
            raise RuntimeError("falla a mitad de camino")
    assert clients.get_all_clients() == []


def test_transaction_commits_when_block_succeeds(isolated_db):
    clients = ClientService()
    with connection.transaction() as conn:
        clients.create_client("Uno", conn=conn)
        clients.create_client("Dos", conn=conn)
    assert len(clients.get_all_clients()) == 2


def _old_database(path) -> None:
    """A database created with the original schema, with some data."""
    conn = sqlite3.connect(path)
    conn.executescript(legacy_schema_sql())
    conn.execute("INSERT INTO clients (name) VALUES ('Ana')")
    conn.execute("INSERT INTO vehicles (client_id, plate) VALUES (1, 'AA111AA')")
    for status in (1, 2, 3, 4, 5):
        conn.execute("INSERT INTO orders (vehicle_id, status_id) VALUES (1, ?)", (status,))
    conn.commit()
    conn.close()


def test_migration_moves_removed_statuses_to_pending(tmp_path, monkeypatch):
    db_file = tmp_path / "old.db"
    _old_database(db_file)
    monkeypatch.setattr(connection, "db_path", db_file)

    with connection.get_connection() as conn:
        statuses = [r[0] for r in conn.execute("SELECT id FROM order_status ORDER BY id")]
        orders = [r[0] for r in conn.execute("SELECT status_id FROM orders ORDER BY id")]
        has_settings = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='settings'"
        ).fetchone()

    assert statuses == [1, 5, 6]
    assert orders == [1, 1, 1, 1, 5]
    assert has_settings is not None


def test_new_database_has_only_the_three_statuses(isolated_db):
    with connection.get_connection() as conn:
        names = [r[0] for r in conn.execute("SELECT name FROM order_status ORDER BY id")]
    assert names == ["pending", "completed", "cancelled"]
