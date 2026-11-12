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


def legacy_schema_sql() -> str:
    """Schema of a database created before migrations were versioned (the
    original May 2026 schema): statuses 1-6, no parts/charge/notes columns on
    orders, no incomes or settings tables, appointments.duration_minutes, and
    no normalized-plate index."""
    sql = connection.schema_path.read_text(encoding="utf-8")
    sql = sql[: sql.index("-- SETTINGS")]
    sql = sql.replace(
        "INSERT INTO order_status (id, name) VALUES\n(1, 'pending'),",
        "INSERT INTO order_status (id, name) VALUES\n(1, 'pending'),\n(2, 'scheduled'),"
        "\n(3, 'in_progress'),\n(4, 'waiting_parts'),",
    )
    for line in (
        "    parts_cost REAL,\n",
        "    customer_charge REAL,\n",
        "    completion_notes TEXT,\n",
    ):
        assert line in sql
        sql = sql.replace(line, "")
    start = sql.index("CREATE TABLE incomes")
    end = sql.index("ON incomes(date);") + len("ON incomes(date);")
    sql = sql[:start] + sql[end:]
    sql = sql.replace(
        "    reason TEXT, \n",
        "    reason TEXT, \n    duration_minutes INTEGER DEFAULT 60,\n",
    )
    assert "duration_minutes" in sql
    return strip_appointment_order_link(sql)


def strip_appointment_order_link(sql: str) -> str:
    """Remove appointments.order_id (added in migration v3) from schema text."""
    for old, new in (
        ("    order_id INTEGER,\n", ""),
        (
            "    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),\n"
            "    FOREIGN KEY (order_id) REFERENCES orders(id)\n",
            "    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)\n",
        ),
    ):
        assert old in sql
        sql = sql.replace(old, new)
    return sql
