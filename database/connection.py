"""SQLite connection, one-time initialization and transactions.

Importing this module has no side effects: folders are created and the schema
is migrated the first time a given database file is opened (or explicitly with
``init_database()`` at startup).
"""

import sqlite3
import sys
from collections.abc import Generator
from contextlib import contextmanager
from os import getenv
from pathlib import Path

from database.migrations import migrate

BASE_DIR = Path(__file__).resolve().parent
APP_DIR_NAME = "GarageManager"
DB_FILE_NAME = "garage_manager.db"


def _user_data_dir_path() -> Path:
    local_appdata = getenv("LOCALAPPDATA")
    if local_appdata:
        return Path(local_appdata) / APP_DIR_NAME
    return Path.home() / "AppData" / "Local" / APP_DIR_NAME


def _get_user_data_dir() -> Path:
    data_dir = _user_data_dir_path()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_user_data_dir() -> Path:
    """Folder for the database, backups and log file (created if missing)."""
    return _get_user_data_dir()


def _resolve_schema_path() -> Path:
    # PyInstaller onefile/onedir extracts data files under _MEIPASS.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_schema = Path(meipass) / "database" / "schema.sql"
            if bundled_schema.exists():
                return bundled_schema
    return BASE_DIR / "schema.sql"


# Tests replace ``db_path`` with a temporary file (monkeypatch).
db_path = _user_data_dir_path() / DB_FILE_NAME
schema_path = _resolve_schema_path()

# Database files already created/migrated by this process.
_initialized: set[Path] = set()


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(path: Path | None = None) -> int:
    """Create or migrate the database. Safe to call more than once.

    Returns the schema version. Raises
    ``database.migrations.DatabaseTooNewError`` if the file comes from a
    newer version of the app.
    """
    target = Path(path or db_path)
    conn = _connect(target)
    try:
        version = migrate(conn, schema_path)
    finally:
        conn.close()
    _initialized.add(target.resolve())
    return version


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    path = Path(db_path)
    if path.resolve() not in _initialized:
        init_database(path)
    conn = _connect(path)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(
    conn: sqlite3.Connection | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Run a block of writes as a single unit.

    * ``conn=None``: opens a connection, commits if the block succeeds and
      rolls back if it raises.
    * An existing ``conn``: joins the caller's transaction. Nothing is committed
      here; the caller that opened the transaction decides.

    This lets a service method work on its own or as one step of a larger
    operation (for example, booking an appointment that also creates the client
    and the vehicle) without leaving half-saved data behind.
    """
    if conn is not None:
        yield conn
        return
    with get_connection() as own:
        try:
            yield own
            own.commit()
        except BaseException:
            own.rollback()
            raise
