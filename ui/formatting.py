"""How amounts and dates are shown to the user (U2).

Pure Python (no Qt) so it can be unit-tested. The database always stores ISO
dates (YYYY-MM-DD) and plain numbers; only the presentation changes:

* Spanish (Argentina): ``$ 1.234,56`` and ``31/10/2026``
* English (US):        ``$1,234.56`` and ``10/31/2026``
"""

from __future__ import annotations

from datetime import date

SUPPORTED_LANGUAGES = ("es", "en")


def format_money(value, language: str) -> str:
    try:
        amount = round(float(value), 2) + 0.0  # no "-0.00"
    except (TypeError, ValueError):
        return "$ —"
    digits = f"{abs(amount):,.2f}"
    if language == "es":
        digits = digits.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
        text = f"$ {digits}"
    else:
        text = f"${digits}"
    return f"-{text}" if amount < 0 else text


def format_date(value, language: str) -> str:
    """ISO date (or datetime text starting with one) -> localized date.
    Anything that is not a date is returned unchanged; empty -> "—"."""
    if value is None or str(value).strip() == "":
        return "—"
    raw = str(value).strip()
    try:
        d = date.fromisoformat(raw[:10])
    except ValueError:
        return raw
    if language == "es":
        return f"{d.day:02d}/{d.month:02d}/{d.year}"
    return f"{d.month:02d}/{d.day:02d}/{d.year}"


def qt_date_format(language: str) -> str:
    """Display format for QDateEdit, matching ``format_date``."""
    return "dd/MM/yyyy" if language == "es" else "MM/dd/yyyy"
