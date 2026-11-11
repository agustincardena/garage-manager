"""Versioned database migrations.

The schema version is stored in SQLite's ``PRAGMA user_version``:

* **New database** (no tables): ``schema.sql`` already describes the latest
  schema, so it is applied and the version is set to ``LATEST_VERSION``.
* **Existing database with version 0** (created before versioning): the old
  ad-hoc checks bring it to the version-1 baseline, whatever state it was in.
* Then every migration newer than the stored version runs **once**, each in
  its own transaction together with the version bump: a failed migration
  leaves the database exactly as it was.

To change the schema: update ``schema.sql`` (for new databases) **and** add a
function to ``MIGRATIONS`` with the next version number (for existing ones).
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseTooNewError(RuntimeError):
    """The database was written by a newer version of the app."""


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def get_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _set_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)}")


# --------------------------------------------------------------------------
# Version 1: baseline. Brings any pre-versioning database to the schema as of
# phase 1 (the checks that used to run on every connection).
# --------------------------------------------------------------------------

def _v1_baseline(conn: sqlite3.Connection) -> None:
    order_cols = _columns(conn, "orders")
    for column, sql_type in (
        ("parts_cost", "REAL"),
        ("customer_charge", "REAL"),
        ("completion_notes", "TEXT"),
    ):
        if column not in order_cols:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {column} {sql_type}")

    if not _table_exists(conn, "incomes"):
        conn.execute(
            """
            CREATE TABLE incomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                description TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount >= 0),
                category TEXT
            )
            """
        )
        conn.execute("CREATE INDEX idx_incomes_date ON incomes(date)")

    if "duration_minutes" in _columns(conn, "appointments"):
        conn.execute("ALTER TABLE appointments DROP COLUMN duration_minutes")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    # Statuses 2 (scheduled), 3 (in_progress), 4 (waiting_parts) were removed.
    conn.execute("UPDATE orders SET status_id = 1 WHERE status_id IN (2, 3, 4)")
    conn.execute("DELETE FROM order_status WHERE id IN (2, 3, 4)")


# --------------------------------------------------------------------------
# Version 2 (B7): plates are unique ignoring case and surrounding spaces.
# --------------------------------------------------------------------------

def _v2_unique_plates(conn: sqlite3.Connection) -> None:
    duplicates = [
        row[0]
        for row in conn.execute(
            """
            SELECT UPPER(TRIM(plate))
            FROM vehicles
            WHERE TRIM(COALESCE(plate, '')) <> ''
            GROUP BY UPPER(TRIM(plate))
            HAVING COUNT(*) > 1
            """
        )
    ]
    if duplicates:
        # Do not block the app: the service layer already rejects new
        # duplicates. The index can be added once these are fixed by hand.
        logger.warning(
            "Duplicate plates found, unique plate index not created: %s",
            ", ".join(duplicates),
        )
        return

    conn.execute(
        """
        UPDATE vehicles
        SET plate = NULLIF(UPPER(TRIM(plate)), '')
        WHERE plate IS NOT NULL AND plate IS NOT NULLIF(UPPER(TRIM(plate)), '')
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicles_plate_normalized
        ON vehicles(UPPER(TRIM(plate)))
        WHERE plate IS NOT NULL
        """
    )


Migration = Callable[[sqlite3.Connection], None]

MIGRATIONS: list[tuple[int, Migration]] = [
    (1, _v1_baseline),
    (2, _v2_unique_plates),
]
LATEST_VERSION = MIGRATIONS[-1][0]


def migrate(conn: sqlite3.Connection, schema_path: Path) -> int:
    """Bring the database to ``LATEST_VERSION``. Returns the final version."""
    version = get_version(conn)
    if version > LATEST_VERSION:
        raise DatabaseTooNewError(
            f"Database version {version} is newer than this app supports "
            f"({LATEST_VERSION}). Update Garage Manager."
        )

    if not _table_exists(conn, "clients"):
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        _set_version(conn, LATEST_VERSION)
        conn.commit()
        logger.info("New database created at version %s", LATEST_VERSION)
        return LATEST_VERSION

    for target, migration in MIGRATIONS:
        if target <= version:
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            migration(conn)
            _set_version(conn, target)
            conn.commit()
        except BaseException:
            conn.rollback()
            logger.exception("Migration to version %s failed", target)
            raise
        logger.info("Database migrated to version %s", target)
        version = target
    return version
