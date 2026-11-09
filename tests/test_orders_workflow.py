"""Work orders: lifecycle (pending -> completed / cancelled), validations, listings."""

from __future__ import annotations

from datetime import date

import pytest

from services.client_service import ClientService
from services.order_item_service import OrderItemService
from services.order_service import OrderService
from services.order_status import OrderStatus
from services.vehicle_service import VehicleService
from tests.helpers import completed_at


def _vehicle(plate: str = "AB123CD") -> int:
    cid = ClientService().create_client("Cliente Test", phone="341000")
    return VehicleService().create_vehicle(cid, brand="Ford", model="Ka", plate=plate)


def test_three_orders_with_each_status_are_listed(isolated_db) -> None:
    """3 clients/vehicles, one order in each status; the general listing has all 3."""
    clients = ClientService()
    vehicles = VehicleService()
    orders = OrderService()

    vids = [
        vehicles.create_vehicle(clients.create_client(f"Cliente {i}", phone=f"100{i}"), plate=f"PY-{i}")
        for i in range(3)
    ]
    oid_pending = orders.create_order(vids[0], notes="Pendiente")
    oid_done = orders.create_order(vids[1], notes="Terminada")
    oid_cancelled = orders.create_order(vids[2], notes="Cancelada")

    orders.complete_order(oid_done, parts_cost=10.0, customer_charge=150.0, completion_notes="ok")
    orders.cancel_order(oid_cancelled)

    assert orders.get_order_by_id(oid_pending)["status_id"] == OrderStatus.PENDING
    assert orders.get_order_by_id(oid_done)["status_id"] == OrderStatus.COMPLETED
    assert orders.get_order_by_id(oid_cancelled)["status_id"] == OrderStatus.CANCELLED
    assert {o["id"] for o in orders.get_all_orders()} == {oid_pending, oid_done, oid_cancelled}


def test_removed_intermediate_status_methods_are_gone(isolated_db):
    assert not hasattr(OrderService, "start_order")
    assert not hasattr(OrderService, "schedule_order")


@pytest.mark.parametrize(
    "parts, charge, error_key",
    [
        (0, 0, "errors.order.charge_must_be_positive"),
        (0, -5, "errors.order.charge_must_be_positive"),
        (-1, 100, "errors.order.parts_cost_negative"),
    ],
)
def test_complete_order_validates_amounts(isolated_db, parts, charge, error_key):
    oid = OrderService().create_order(_vehicle())
    with pytest.raises(ValueError, match=error_key):
        OrderService().complete_order(oid, parts_cost=parts, customer_charge=charge)
    assert OrderService().get_order_by_id(oid)["status_id"] == OrderStatus.PENDING


def test_complete_order_saves_rounded_financials_and_notes(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=200.004, customer_charge=500.1 + 0.2, completion_notes="  ok  ")
    row = orders.get_order_by_id(oid)
    assert row["status_id"] == OrderStatus.COMPLETED
    assert row["parts_cost"] == 200.0
    assert row["customer_charge"] == 500.3
    assert row["completion_notes"] == "ok"
    assert row["completed_at"] == date.today().isoformat()


def test_complete_order_does_not_create_items(isolated_db):
    """B6: reports use the order's charge/parts; no synthetic item is inserted."""
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=30, customer_charge=120)
    assert OrderItemService().get_items_by_order(oid) == []


def test_pending_and_history_listings(isolated_db):
    orders = OrderService()
    vid = _vehicle()
    pending = orders.create_order(vid, notes="pendiente")
    done = orders.create_order(vid, notes="terminada")
    cancelled = orders.create_order(vid, notes="cancelada")
    orders.complete_order(done, parts_cost=0, customer_charge=50)
    orders.cancel_order(cancelled)

    assert {o["id"] for o in orders.get_pending_workshop_orders()} == {pending}
    assert {o["id"] for o in orders.get_history_orders()} == {done}


# --- B3: errors are raised instead of printed -------------------------------

def test_b3_completing_twice_raises_and_keeps_first_values(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    with pytest.raises(ValueError, match="errors.order.not_pending"):
        orders.complete_order(oid, parts_cost=0, customer_charge=999)
    assert orders.get_order_by_id(oid)["customer_charge"] == 100


def test_b3_cancelled_order_cannot_be_completed(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.cancel_order(oid)
    with pytest.raises(ValueError, match="errors.order.not_pending"):
        orders.complete_order(oid, parts_cost=0, customer_charge=100)
    row = orders.get_order_by_id(oid)
    assert row["status_id"] == OrderStatus.CANCELLED
    assert row["customer_charge"] is None


def test_b3_completed_order_cannot_be_cancelled(isolated_db):
    """Cancelling a completed order would silently remove its revenue."""
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    with pytest.raises(ValueError, match="errors.order.not_pending"):
        orders.cancel_order(oid)
    assert orders.get_order_by_id(oid)["status_id"] == OrderStatus.COMPLETED


@pytest.mark.parametrize("action", ["complete", "cancel"])
def test_b3_unknown_order_raises_not_found(isolated_db, action):
    orders = OrderService()
    with pytest.raises(ValueError, match="errors.order.not_found"):
        if action == "complete":
            orders.complete_order(9999, parts_cost=0, customer_charge=100)
        else:
            orders.cancel_order(9999)


# --- B1: dates come from the local clock, not SQLite's UTC CURRENT_DATE ------

def test_b1_order_dates_use_local_date(isolated_db, tz_where_local_date_differs_from_utc):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    row = orders.get_order_by_id(oid)
    assert row["created_at"] == date.today().isoformat()
    assert completed_at(oid) == date.today().isoformat()


def test_b1_today_can_be_pinned_through_clock(isolated_db, monkeypatch):
    from services import clock

    monkeypatch.setattr(clock, "today_iso", lambda: "2026-10-31")
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    assert completed_at(oid) == "2026-10-31"
