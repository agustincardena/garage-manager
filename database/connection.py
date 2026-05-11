import sqlite3
import sys
from collections.abc import Generator
from contextlib import contextmanager
from os import getenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
APP_DIR_NAME = "GarageManager"


def _get_user_data_dir() -> Path:
    local_appdata = getenv("LOCALAPPDATA")
    if local_appdata:
        data_dir = Path(local_appdata) / APP_DIR_NAME
    else:
        data_dir = Path.home() / "AppData" / "Local" / APP_DIR_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _resolve_schema_path() -> Path:
    # PyInstaller onefile/onedir extracts data files under _MEIPASS.
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled_schema = Path(meipass) / "database" / "schema.sql"
            if bundled_schema.exists():
                return bundled_schema
    return BASE_DIR / "schema.sql"


db_path = _get_user_data_dir() / "garage_manager.db"
schema_path = _resolve_schema_path()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='clients'"
    )
    if cur.fetchone() is not None:
        return
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def _apply_migrations(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='orders'"
    )
    if cur.fetchone() is None:
        return
    cur.execute("PRAGMA table_info(orders)")
    cols = {row["name"] for row in cur.fetchall()}
    if "parts_cost" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN parts_cost REAL")
    if "customer_charge" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN customer_charge REAL")
    if "completion_notes" not in cols:
        cur.execute("ALTER TABLE orders ADD COLUMN completion_notes TEXT")

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='incomes'"
    )
    if cur.fetchone() is None:
        cur.execute(
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
        cur.execute("CREATE INDEX idx_incomes_date ON incomes(date)")

    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'"
    )
    if cur.fetchone() is not None:
        cur.execute("PRAGMA table_info(appointments)")
        appt_cols = {row["name"] for row in cur.fetchall()}
        if "duration_minutes" in appt_cols:
            try:
                cur.execute(
                    "ALTER TABLE appointments DROP COLUMN duration_minutes"
                )
            except sqlite3.OperationalError:
                pass

    conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_schema(conn)
    _apply_migrations(conn)
    try:
        yield conn
    finally:
        conn.close()
