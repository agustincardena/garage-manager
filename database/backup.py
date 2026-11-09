"""Automatic daily backup of the SQLite database.

On startup the app calls :func:`create_daily_backup`. If there is no copy for
today yet, it writes ``backups/garage_manager_YYYY-MM-DD.db`` next to the live
database and keeps only the most recent ``keep`` copies.

The copy uses SQLite's online backup API, so it is consistent even if the
database is open, and it is written to a temporary file first: a copy that
fails half-way never replaces or counts as a valid backup.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_DIR_NAME = "backups"
DEFAULT_KEEP = 14
_PREFIX = "garage_manager_"
_NAME_RE = re.compile(rf"^{_PREFIX}(\d{{4}}-\d{{2}}-\d{{2}})\.db$")


class BackupError(RuntimeError):
    """The backup could not be created or failed its integrity check."""


def backup_dir_for(db_path: Path) -> Path:
    """Default backup folder: ``<folder of the database>/backups``."""
    return Path(db_path).parent / BACKUP_DIR_NAME


def backup_file_name(day: date) -> str:
    return f"{_PREFIX}{day.isoformat()}.db"


def list_backups(backup_dir: Path) -> list[Path]:
    """Backups created by this module, oldest first. Other files are ignored."""
    if not backup_dir.is_dir():
        return []
    files = [p for p in backup_dir.iterdir() if p.is_file() and _NAME_RE.match(p.name)]
    return sorted(files, key=lambda p: p.name)


def create_daily_backup(
    db_path: Path,
    backup_dir: Path | None = None,
    *,
    today: date | None = None,
    keep: int = DEFAULT_KEEP,
) -> Path | None:
    """Create today's backup if it does not exist yet.

    Returns the path of the new backup, or ``None`` when there was nothing to do
    (no database yet, or today's copy already exists).

    Raises :class:`BackupError` if the copy fails or is not a valid database.
    """
    if keep < 1:
        raise ValueError("keep must be at least 1")

    db_path = Path(db_path)
    if not db_path.is_file():
        logger.info("No database at %s yet; skipping backup.", db_path)
        return None

    backup_dir = Path(backup_dir) if backup_dir is not None else backup_dir_for(db_path)
    day = today or date.today()
    target = backup_dir / backup_file_name(day)
    if target.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    try:
        _copy_database(db_path, tmp)
        _check_integrity(tmp)
        tmp.replace(target)
    except (sqlite3.Error, OSError) as exc:
        _remove_quietly(tmp)
        raise BackupError(f"Could not back up {db_path}: {exc}") from exc
    except BackupError:
        _remove_quietly(tmp)
        raise

    logger.info("Backup created: %s", target)
    _rotate(backup_dir, keep)
    return target


def _copy_database(source: Path, destination: Path) -> None:
    _remove_quietly(destination)
    src = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(destination)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _check_integrity(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        result = conn.execute("PRAGMA quick_check").fetchone()
    finally:
        conn.close()
    if not result or result[0] != "ok":
        raise BackupError(f"Backup failed integrity check: {result!r}")


def _rotate(backup_dir: Path, keep: int) -> None:
    backups = list_backups(backup_dir)
    for old in backups[:-keep]:
        try:
            old.unlink()
            logger.info("Old backup removed: %s", old)
        except OSError:
            logger.warning("Could not remove old backup %s", old, exc_info=True)


def _remove_quietly(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning("Could not remove temporary file %s", path, exc_info=True)
