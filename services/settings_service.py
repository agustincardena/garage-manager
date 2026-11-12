"""Workshop settings stored in the database (so they travel with backups)."""

from __future__ import annotations

import sqlite3

from database.connection import transaction

SLOT_CAPACITY_KEY = "appointments.slot_capacity"
DEFAULT_SLOT_CAPACITY = 1
MIN_SLOT_CAPACITY = 1
MAX_SLOT_CAPACITY = 20

LANGUAGE_KEY = "ui.language"
SUPPORTED_LANGUAGES = ("es", "en")
DEFAULT_LANGUAGE = "es"


def resolve_language(saved: str | None, system_locale_name: str | None) -> str:
    """U1: language to start with. The user's saved choice wins; otherwise the
    system language if supported (e.g. "es_AR" -> "es"); otherwise Spanish."""
    if saved in SUPPORTED_LANGUAGES:
        return saved
    system = (system_locale_name or "").lower()[:2]
    if system in SUPPORTED_LANGUAGES:
        return system
    return DEFAULT_LANGUAGE


class SettingsService:

    def get_slot_capacity(self, conn: sqlite3.Connection | None = None) -> int:
        """How many appointments can share the same date and time."""
        with transaction(conn) as c:
            row = c.execute(
                "SELECT value FROM settings WHERE key = ?", (SLOT_CAPACITY_KEY,)
            ).fetchone()
        if row is None:
            return DEFAULT_SLOT_CAPACITY
        try:
            value = int(row[0])
        except (TypeError, ValueError):
            return DEFAULT_SLOT_CAPACITY
        return min(max(value, MIN_SLOT_CAPACITY), MAX_SLOT_CAPACITY)

    def set_slot_capacity(self, value: int) -> None:
        try:
            capacity = int(value)
        except (TypeError, ValueError):
            raise ValueError("errors.settings.slot_capacity_range") from None
        if not MIN_SLOT_CAPACITY <= capacity <= MAX_SLOT_CAPACITY:
            raise ValueError("errors.settings.slot_capacity_range")
        with transaction() as c:
            c.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (SLOT_CAPACITY_KEY, str(capacity)),
            )

    def get_language(self, conn: sqlite3.Connection | None = None) -> str | None:
        """The language the user picked, or None if they never picked one."""
        with transaction(conn) as c:
            row = c.execute(
                "SELECT value FROM settings WHERE key = ?", (LANGUAGE_KEY,)
            ).fetchone()
        if row is None or row[0] not in SUPPORTED_LANGUAGES:
            return None
        return row[0]

    def set_language(self, code: str) -> None:
        if code not in SUPPORTED_LANGUAGES:
            raise ValueError("errors.settings.language_unsupported")
        with transaction() as c:
            c.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (LANGUAGE_KEY, code),
            )
