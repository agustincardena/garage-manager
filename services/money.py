"""Money helpers. Amounts are stored as REAL rounded to 2 decimals."""

from __future__ import annotations


def round_money(value) -> float:
    """Round to cents. ``+ 0.0`` turns ``-0.0`` into ``0.0`` so it never
    displays as "-0.00"."""
    return round(float(value), 2) + 0.0
