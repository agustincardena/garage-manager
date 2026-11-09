"""Single source for "today" in the app's local time.

SQLite's CURRENT_DATE is UTC: in Argentina (UTC-3) anything saved after
21:00 would be dated the next day. Services pass this date explicitly instead.
Tests can monkeypatch ``today_iso`` to pin a date.
"""

from __future__ import annotations

from datetime import date


def today() -> date:
    return date.today()


def today_iso() -> str:
    return today().isoformat()
