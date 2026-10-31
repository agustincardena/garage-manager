"""Automatic daily backup (database/backup.py)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from database import backup
from services.client_service import ClientService


def _client_names(db_file) -> list[str]:
    conn = sqlite3.connect(db_file)
    try:
        return [r[0] for r in conn.execute("SELECT name FROM clients ORDER BY id")]
    finally:
        conn.close()


def test_no_database_means_no_backup(tmp_path):
    assert backup.create_daily_backup(tmp_path / "missing.db") is None
    assert not (tmp_path / backup.BACKUP_DIR_NAME).exists()


def test_backup_is_a_full_copy_in_default_folder(isolated_db):
    ClientService().create_client("Ana")
    day = date(2026, 10, 31)

    created = backup.create_daily_backup(isolated_db, today=day)

    assert created == isolated_db.parent / "backups" / "garage_manager_2026-10-31.db"
    assert _client_names(created) == ["Ana"]
    assert not list(created.parent.glob("*.tmp"))


def test_only_one_backup_per_day(isolated_db, tmp_path):
    folder = tmp_path / "bk"
    day = date(2026, 10, 31)
    first = backup.create_daily_backup(isolated_db, folder, today=day)
    ClientService().create_client("Creado después")

    assert backup.create_daily_backup(isolated_db, folder, today=day) is None
    assert backup.list_backups(folder) == [first]
    assert _client_names(first) == []  # today's copy is not overwritten


def test_rotation_keeps_most_recent_and_ignores_other_files(isolated_db, tmp_path):
    folder = tmp_path / "bk"
    folder.mkdir()
    unrelated = folder / "mi_copia_manual.db"
    unrelated.write_text("no tocar")
    start = date(2026, 10, 1)

    for i in range(5):
        backup.create_daily_backup(isolated_db, folder, today=start + timedelta(days=i), keep=3)

    names = [p.name for p in backup.list_backups(folder)]
    assert names == [
        "garage_manager_2026-10-03.db",
        "garage_manager_2026-10-04.db",
        "garage_manager_2026-10-05.db",
    ]
    assert unrelated.read_text() == "no tocar"


def test_backup_works_while_database_is_open(isolated_db, tmp_path):
    conn = sqlite3.connect(isolated_db)
    try:
        conn.execute("INSERT INTO clients (name) VALUES ('En uso')")
        conn.commit()
        created = backup.create_daily_backup(isolated_db, tmp_path / "bk")
    finally:
        conn.close()
    assert _client_names(created) == ["En uso"]


def test_corrupt_database_raises_and_leaves_no_files(tmp_path):
    bad = tmp_path / "garage_manager.db"
    bad.write_bytes(b"esto no es una base sqlite" * 100)
    folder = tmp_path / "bk"

    with pytest.raises(backup.BackupError):
        backup.create_daily_backup(bad, folder)

    assert list(folder.iterdir()) == []


def test_keep_must_be_positive(isolated_db):
    with pytest.raises(ValueError):
        backup.create_daily_backup(isolated_db, keep=0)
