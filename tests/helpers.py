"""Small helpers shared by tests."""

from __future__ import annotations

import database.connection as connection


def completed_at(order_id: int) -> str:
    """Date stored by ``complete_order`` (read back, since the service picks it)."""
    with connection.get_connection() as conn:
        row = conn.execute(
            "SELECT completed_at FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
    return row["completed_at"]
