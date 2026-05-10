"""
Integration test: clients, vehicles, orders with distinct statuses on an isolated SQLite DB.

Uses a temporary database file so your real ``database/garage_manager.db`` is never touched.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.client_service import ClientService
from services.order_service import OrderService
from services.vehicle_service import VehicleService


def _init_schema(db_file: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    schema_path = root / "database" / "schema.sql"
    sql = schema_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Point ``database.connection`` at a fresh DB and apply ``schema.sql``."""
    db_file = tmp_path / "pytest_garage_orders.db"
    monkeypatch.setattr("database.connection.db_path", db_file)
    _init_schema(db_file)
    yield db_file


def test_three_clients_vehicles_orders_distinct_statuses_general_report_count(
    isolated_db,
) -> None:
    """
    - 3 clients, each with one vehicle (unique plates).
    - 3 work orders: pending (1), in progress (3), completed (5).
    - General order query returns exactly 3 rows.
    """
    clients = ClientService()
    vehicles = VehicleService()
    orders = OrderService()

    cid1 = clients.create_client("Pytest Client Alfa", phone="1001", email=None)
    cid2 = clients.create_client("Pytest Client Beta", phone="1002", email=None)
    cid3 = clients.create_client("Pytest Client Gamma", phone="1003", email=None)

    vid1 = vehicles.create_vehicle(cid1, brand="MakeA", model="M1", plate="PY-A-001")
    vid2 = vehicles.create_vehicle(cid2, brand="MakeB", model="M2", plate="PY-B-002")
    vid3 = vehicles.create_vehicle(cid3, brand="MakeC", model="M3", plate="PY-C-003")

    oid_pending = orders.create_order(
        vid1, scheduled_date="2030-01-15", scheduled_time="09:00", notes="Order pending"
    )
    oid_progress = orders.create_order(
        vid2, scheduled_date="2030-01-16", scheduled_time="10:00", notes="Order in progress"
    )
    oid_done = orders.create_order(
        vid3, scheduled_date="2030-01-17", scheduled_time="11:00", notes="Order to complete"
    )

    orders.start_order(oid_progress)
    orders.start_order(oid_done)
    orders.complete_order(oid_done, parts_cost=10.0, customer_charge=150.0, completion_notes="pytest")

    row_pending = orders.get_order_by_id(oid_pending)
    row_progress = orders.get_order_by_id(oid_progress)
    row_done = orders.get_order_by_id(oid_done)

    assert row_pending is not None and row_pending["status_id"] == 1
    assert row_progress is not None and row_progress["status_id"] == 3
    assert row_done is not None and row_done["status_id"] == 5

    all_orders = orders.get_all_orders()
    assert len(all_orders) == 3, (
        f"Expected exactly 3 orders in general listing, got {len(all_orders)}: {all_orders!r}"
    )

    ids = {o["id"] for o in all_orders}
    assert ids == {oid_pending, oid_progress, oid_done}
