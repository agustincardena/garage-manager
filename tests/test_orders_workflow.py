"""Work orders: lifecycle, validations and listings."""

from __future__ import annotations

import pytest

from services.client_service import ClientService
from services.order_item_service import OrderItemService
from services.order_service import OrderService
from services.vehicle_service import VehicleService


def _vehicle(plate: str = "AB123CD") -> int:
    cid = ClientService().create_client("Cliente Test", phone="341000")
    return VehicleService().create_vehicle(cid, brand="Ford", model="Ka", plate=plate)


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
    assert OrderService().get_order_by_id(oid)["status_id"] == 1


def test_complete_order_saves_financials_and_notes(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=200, customer_charge=500, completion_notes="  ok  ")
    row = orders.get_order_by_id(oid)
    assert row["status_id"] == 5
    assert row["parts_cost"] == 200
    assert row["customer_charge"] == 500
    assert row["completion_notes"] == "ok"
    assert row["completed_at"] is not None


def test_complete_order_without_items_adds_single_closure_item(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.complete_order(oid, parts_cost=30, customer_charge=120)
    items = OrderItemService().get_items_by_order(oid)
    assert len(items) == 1
    assert items[0]["price"] == 120
    assert items[0]["cost"] == 30


def test_complete_order_with_items_does_not_add_closure_item(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    OrderItemService().create_item(oid, "Mano de obra", 100, 0)
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    assert len(OrderItemService().get_items_by_order(oid)) == 1


def test_pending_and_history_listings(isolated_db):
    orders = OrderService()
    vid = _vehicle()
    pending = orders.create_order(vid, notes="pendiente")
    done = orders.create_order(vid, notes="terminada")
    cancelled = orders.create_order(vid, notes="cancelada")
    orders.complete_order(done, parts_cost=0, customer_charge=50)
    orders.cancel_order(cancelled)

    pending_ids = {o["id"] for o in orders.get_pending_workshop_orders()}
    history_ids = {o["id"] for o in orders.get_history_orders()}
    assert pending_ids == {pending}
    assert history_ids == {done}


def test_cancelled_order_cannot_be_completed(isolated_db):
    orders = OrderService()
    oid = orders.create_order(_vehicle())
    orders.cancel_order(oid)
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    row = orders.get_order_by_id(oid)
    assert row["status_id"] == 6
    assert row["customer_charge"] is None
