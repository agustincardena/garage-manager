"""Known bugs from the improvement plan, written as the *expected* behaviour.

They are marked ``xfail(strict=True)``: they fail today, and the moment a fix
makes one pass, pytest reports it as XPASS -> error. When that happens, delete
the ``xfail`` marker so the test becomes a normal regression test.

Codes (B1, B3, ...) refer to the improvement plan.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone

import pytest

from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.order_item_service import OrderItemService
from services.order_service import OrderService
from services.report_service import ReportService
from services.vehicle_service import VehicleService
from tests.helpers import completed_at


def _vehicle(plate: str = "AB123CD") -> tuple[int, int]:
    cid = ClientService().create_client("Ana")
    return cid, VehicleService().create_vehicle(cid, plate=plate)


@pytest.fixture
def tz_where_local_date_differs_from_utc(monkeypatch):
    """Switch the process time zone so that local date != UTC date right now."""
    if not hasattr(time, "tzset"):
        pytest.skip("time.tzset is not available on this platform (Windows)")
    utc_hour = datetime.now(timezone.utc).hour
    # POSIX TZ strings have inverted signs: "Etc/GMT+12" is UTC-12.
    tz = "Etc/GMT+12" if utc_hour < 12 else "Etc/GMT-14"
    monkeypatch.setenv("TZ", tz)
    time.tzset()
    assert date.today() != datetime.now(timezone.utc).date()
    yield
    monkeypatch.undo()
    time.tzset()


@pytest.mark.xfail(strict=True, reason="B1: dates are stored with SQLite CURRENT_DATE (UTC)")
def test_b1_completed_order_uses_local_date(isolated_db, tz_where_local_date_differs_from_utc):
    _, vid = _vehicle()
    oid = OrderService().create_order(vid)
    OrderService().complete_order(oid, parts_cost=0, customer_charge=100)
    assert completed_at(oid) == date.today().isoformat()


@pytest.mark.xfail(strict=True, reason="B3: completing an already closed order fails silently")
def test_b3_completing_twice_raises(isolated_db):
    _, vid = _vehicle()
    orders = OrderService()
    oid = orders.create_order(vid)
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    with pytest.raises(ValueError):
        orders.complete_order(oid, parts_cost=0, customer_charge=999)


@pytest.mark.xfail(strict=True, reason="B3: cancelling an unknown order fails silently")
def test_b3_cancel_unknown_order_raises(isolated_db):
    with pytest.raises(ValueError):
        OrderService().cancel_order(9999)


@pytest.mark.xfail(strict=True, reason="B5: float residue makes a zero profit non-zero")
def test_b5_profit_is_rounded(isolated_db):
    from services.expense_service import ExpenseService
    from services.income_service import IncomeService

    IncomeService().create_income("a", 0.1, date="2025-01-10")
    IncomeService().create_income("b", 0.2, date="2025-01-10")
    ExpenseService().create_expense("c", 0.3, date="2025-01-10")
    assert ReportService().get_monthly_summary(2025, 1)["profit"] == 0.0


@pytest.mark.xfail(strict=True, reason="B6: summary uses orders, total profit uses order_items")
def test_b6_profit_has_a_single_source(isolated_db):
    _, vid = _vehicle()
    orders = OrderService()
    oid = orders.create_order(vid)
    OrderItemService().create_item(oid, "Mano de obra", 100, 20)
    orders.complete_order(oid, parts_cost=10, customer_charge=150)
    y, m, _ = completed_at(oid).split("-")

    reports = ReportService()
    assert reports.get_monthly_summary(int(y), int(m))["profit"] == reports.get_total_profit()


@pytest.mark.xfail(strict=True, reason="B7: update_vehicle neither normalizes nor checks plates")
def test_b7_update_vehicle_rejects_duplicate_plate(isolated_db):
    cid, _ = _vehicle("AB123CD")
    other = VehicleService().create_vehicle(cid, plate="ZZ999ZZ")
    with pytest.raises(ValueError, match="errors.vehicle.duplicate_plate"):
        VehicleService().update_vehicle(other, plate="ab123cd")


# B8a lives in the UI: BookingDialog sends ``reason or None`` and the service
# reads ``None`` as "keep the current value". The service itself clears the
# reason when given "" (covered below as a normal test).
def test_b8a_service_clears_reason_when_given_empty_string(isolated_db):
    cid, vid = _vehicle()
    appts = AppointmentService()
    when = date.today() + timedelta(days=2)
    aid = appts.create_appointment(cid, vid, when, "10:00", reason="Ruido")
    appts.update_appointment(aid, reason="")
    assert not appts.get_appointment_by_id(aid)["reason"]


@pytest.mark.xfail(strict=True, reason="B8b: converted order loses the scheduled date/time")
def test_b8b_converted_order_keeps_schedule(isolated_db):
    cid, vid = _vehicle()
    when = (date.today() + timedelta(days=2)).isoformat()
    aid = AppointmentService().create_appointment(cid, vid, when, "10:00")
    oid = AppointmentService().convert_to_order(aid)
    order = OrderService().get_order_by_id(oid)
    assert (order["scheduled_date"], order["scheduled_time"]) == (when, "10:00")


@pytest.mark.xfail(strict=True, reason="B8c: deleting a client with vehicles raises a raw IntegrityError")
def test_b8c_delete_client_with_vehicles_raises_translated_error(isolated_db):
    cid, _ = _vehicle()
    with pytest.raises(ValueError, match="errors.client.has_vehicles"):
        ClientService().delete_client(cid)

