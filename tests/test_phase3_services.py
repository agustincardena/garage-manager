"""Phase 3 services: corrections (B4), walk-in orders (F3), report ledgers that
add up (F4) and client/vehicle editing (F5)."""

from __future__ import annotations

import pytest

from database.connection import get_connection
from services.client_service import ClientService
from services.expense_service import ExpenseService
from services.income_service import IncomeService
from services.order_service import OrderService
from services.order_status import OrderStatus
from services.report_service import ReportService
from services.vehicle_service import VehicleService
from tests.helpers import completed_at


@pytest.fixture
def ana(isolated_db):
    cid = ClientService().create_client("Ana", phone="341")
    vid = VehicleService().create_vehicle(cid, plate="AA111AA", brand="Ford")
    return cid, vid


def _counts() -> dict[str, int]:
    with get_connection() as conn:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("clients", "vehicles", "orders")
        }


# --- B4: correcting a completed order -----------------------------------------

def test_b4_correction_updates_amounts_and_reports_keeping_date(ana):
    _, vid = ana
    orders = OrderService()
    oid = orders.create_order(vid)
    orders.complete_order(oid, parts_cost=100, customer_charge=15000, completion_notes="x")
    closed = completed_at(oid)
    y, m, _ = (int(p) for p in closed.split("-"))

    orders.correct_completed_order(oid, parts_cost=100.004, customer_charge=1500, completion_notes="")

    row = orders.get_order_by_id(oid)
    assert (row["parts_cost"], row["customer_charge"], row["completion_notes"]) == (100.0, 1500.0, None)
    assert (row["status_id"], completed_at(oid)) == (OrderStatus.COMPLETED, closed)
    assert ReportService().get_monthly_summary(y, m) == {
        "income": 1500.0, "expenses": 100.0, "profit": 1400.0,
    }


def test_b4_only_completed_orders_can_be_corrected(ana):
    _, vid = ana
    orders = OrderService()
    pending = orders.create_order(vid)
    cancelled = orders.create_order(vid)
    orders.cancel_order(cancelled)
    for oid in (pending, cancelled):
        with pytest.raises(ValueError, match="errors.order.not_completed"):
            orders.correct_completed_order(oid, parts_cost=0, customer_charge=10)
    with pytest.raises(ValueError, match="errors.order.not_found"):
        orders.correct_completed_order(9999, parts_cost=0, customer_charge=10)


@pytest.mark.parametrize(
    "parts, charge, key",
    [(0, 0, "errors.order.charge_must_be_positive"), (-1, 10, "errors.order.parts_cost_negative")],
)
def test_b4_correction_validates_amounts(ana, parts, charge, key):
    _, vid = ana
    orders = OrderService()
    oid = orders.create_order(vid)
    orders.complete_order(oid, parts_cost=5, customer_charge=50)
    with pytest.raises(ValueError, match=key):
        orders.correct_completed_order(oid, parts_cost=parts, customer_charge=charge)
    assert orders.get_order_by_id(oid)["customer_charge"] == 50


def test_b4_manual_income_can_be_edited_and_deleted(isolated_db):
    incomes = IncomeService()
    iid = incomes.create_income("Venta aciete", 300, date="2025-03-10")
    incomes.update_income(iid, description=" Venta aceite ", amount=350.555)
    row = incomes.get_incomes_by_month(2025, 3)[0]
    assert (row["description"], row["amount"], row["date"]) == ("Venta aceite", 350.56, "2025-03-10")

    with pytest.raises(ValueError, match="errors.income.description_required"):
        incomes.update_income(iid, description="  ")
    incomes.delete_income(iid)
    assert incomes.get_incomes_by_month(2025, 3) == []
    with pytest.raises(ValueError, match="errors.income.not_found"):
        incomes.delete_income(iid)
    with pytest.raises(ValueError, match="errors.income.not_found"):
        incomes.update_income(iid, amount=1)


# --- F3: walk-in order --------------------------------------------------------

def test_f3_walk_in_order_for_existing_vehicle(ana):
    cid, vid = ana
    oid = OrderService().create_walk_in_order(client_id=cid, vehicle_id=vid, notes="  Cambio de aceite ")
    row = OrderService().get_order_by_id(oid)
    assert (row["status_id"], row["plate"], row["notes"]) == (OrderStatus.PENDING, "AA111AA", "Cambio de aceite")
    assert row["scheduled_date"] is None
    assert oid in {o["id"] for o in OrderService().get_pending_workshop_orders()}


def test_f3_walk_in_order_creates_client_and_vehicle(isolated_db):
    oid = OrderService().create_walk_in_order(
        new_client={"name": "Beto Paz", "phone": "341"},
        new_vehicle={"plate": "bb222bb", "brand": "Fiat"},
    )
    row = OrderService().get_order_by_id(oid)
    assert (row["client"], row["plate"]) == ("Beto Paz", "BB222BB")
    assert _counts() == {"clients": 1, "vehicles": 1, "orders": 1}


def test_f3_walk_in_order_is_all_or_nothing(ana):
    before = _counts()
    with pytest.raises(ValueError, match="errors.vehicle.belongs_to_other_client"):
        OrderService().create_walk_in_order(
            new_client={"name": "Beto", "phone": "1"},
            new_vehicle={"plate": "aa111aa"},
        )
    assert _counts() == before


def test_f3_walk_in_order_with_confirmed_transfer(ana):
    _, vid = ana
    oid = OrderService().create_walk_in_order(
        new_client={"name": "Beto", "phone": "1"},
        new_vehicle={"plate": "aa111aa"},
        reassign_vehicle=True,
    )
    assert OrderService().get_order_by_id(oid)["client"] == "Beto"
    assert VehicleService().get_vehicle_by_id(vid)["client"] == "Beto"


# --- F4: ledgers add up to the totals ------------------------------------------

def test_f4_order_ledger_plus_manual_rows_equal_totals(ana):
    _, vid = ana
    orders = OrderService()
    done = []
    for parts, charge in ((200, 1000), (0, 500)):
        oid = orders.create_order(vid)
        orders.complete_order(oid, parts_cost=parts, customer_charge=charge)
        done.append(oid)
    orders.create_order(vid)  # pending: not in the ledger
    y, m, _ = (int(p) for p in completed_at(done[0]).split("-"))
    day = f"{y}-{m:02d}-15"
    IncomeService().create_income("Venta", 300, date=day)
    ExpenseService().create_expense("Luz", 150, date=day)

    reports = ReportService()
    ledger = reports.get_completed_orders_for_period("monthly", y, m)
    summary = reports.get_monthly_summary(y, m)

    assert {r["id"] for r in ledger} == set(done)
    assert ledger[0]["plate"] == "AA111AA" and ledger[0]["client"] == "Ana"
    manual_in = sum(r["amount"] for r in IncomeService().get_incomes_by_month(y, m))
    manual_out = sum(r["amount"] for r in ExpenseService().get_expenses_by_month(y, m))
    assert sum(r["customer_charge"] for r in ledger) + manual_in == summary["income"]
    assert sum(r["parts_cost"] for r in ledger) + manual_out == summary["expenses"]


def test_f4_ledger_respects_period(ana):
    _, vid = ana
    orders = OrderService()
    oid = orders.create_order(vid)
    orders.complete_order(oid, parts_cost=0, customer_charge=100)
    y = int(completed_at(oid)[:4])
    reports = ReportService()
    assert len(reports.get_completed_orders_for_period("yearly", y)) == 1
    assert reports.get_completed_orders_for_period("yearly", y - 1) == []


# --- F5: editing a client and their vehicles ---------------------------------

def test_f5_save_profile_updates_client_and_vehicles(ana):
    cid, vid = ana
    second = VehicleService().create_vehicle(cid, plate="CC333CC")
    ClientService().save_profile(
        cid,
        name=" Ana Gómez ",
        phone="",
        email="ana@mail.com",
        notes=None,
        vehicles=[
            {"id": vid, "brand": "Ford", "model": "Ka", "plate": " aa111ab ", "notes": ""},
            {"id": second, "brand": "", "model": "", "plate": "", "notes": "sin patente"},
        ],
    )
    client = ClientService().get_client_by_id(cid)
    assert (client["name"], client["phone"], client["email"]) == ("Ana Gómez", None, "ana@mail.com")
    v1, v2 = VehicleService().get_vehicle_by_id(vid), VehicleService().get_vehicle_by_id(second)
    assert (v1["model"], v1["plate"]) == ("Ka", "AA111AB")
    assert (v2["plate"], v2["notes"]) == (None, "sin patente")


def test_f5_duplicate_plate_saves_nothing(ana):
    cid, vid = ana
    other_client = ClientService().create_client("Beto")
    VehicleService().create_vehicle(other_client, plate="ZZ999ZZ")
    with pytest.raises(ValueError, match="errors.vehicle.duplicate_plate"):
        ClientService().save_profile(
            cid,
            name="Ana cambiada",
            phone="341",
            email=None,
            notes=None,
            vehicles=[{"id": vid, "brand": "Ford", "model": "", "plate": "zz999zz", "notes": ""}],
        )
    assert ClientService().get_client_by_id(cid)["name"] == "Ana"
    assert VehicleService().get_vehicle_by_id(vid)["plate"] == "AA111AA"


def test_f5_cannot_edit_another_clients_vehicle_or_empty_name(ana):
    cid, _ = ana
    other_client = ClientService().create_client("Beto")
    foreign = VehicleService().create_vehicle(other_client, plate="ZZ999ZZ")
    with pytest.raises(ValueError, match="errors.vehicle.not_found"):
        ClientService().save_profile(
            cid, name="Ana", phone=None, email=None, notes=None,
            vehicles=[{"id": foreign, "plate": "ZZ999ZZ"}],
        )
    with pytest.raises(ValueError, match="errors.client.name_required"):
        ClientService().save_profile(cid, name=" ", phone=None, email=None, notes=None)
    with pytest.raises(ValueError, match="errors.client.not_found"):
        ClientService().save_profile(9999, name="X", phone=None, email=None, notes=None)
