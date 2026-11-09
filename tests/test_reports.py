"""Reports: income = completed order charges + manual incomes;
expenses = manual expenses + parts cost of completed orders."""

from __future__ import annotations

import pytest

from services.client_service import ClientService
from services.expense_service import ExpenseService
from services.income_service import IncomeService
from services.order_service import OrderService
from services.report_service import ReportService
from services.vehicle_service import VehicleService
from tests.helpers import completed_at


@pytest.fixture
def vehicle(isolated_db) -> int:
    cid = ClientService().create_client("Ana")
    return VehicleService().create_vehicle(cid, plate="AB123CD")


def _completed_order(vehicle: int, parts: float, charge: float) -> tuple[int, int, int]:
    """Complete an order; return (order_id, year, month) of its closing date."""
    orders = OrderService()
    oid = orders.create_order(vehicle)
    orders.complete_order(oid, parts_cost=parts, customer_charge=charge)
    y, m, _ = completed_at(oid).split("-")
    return oid, int(y), int(m)


def test_monthly_summary_combines_orders_and_manual_entries(vehicle):
    _, y, m = _completed_order(vehicle, parts=200, charge=1000)
    day = f"{y}-{m:02d}-15"
    IncomeService().create_income("Venta aceite", 300, date=day)
    ExpenseService().create_expense("Luz", 150, date=day)

    summary = ReportService().get_monthly_summary(y, m)

    assert summary == {"income": 1300.0, "expenses": 350.0, "profit": 950.0}


def test_pending_and_cancelled_orders_are_not_counted(vehicle):
    orders = OrderService()
    _, y, m = _completed_order(vehicle, parts=0, charge=500)
    orders.create_order(vehicle)
    cancelled = orders.create_order(vehicle)
    orders.cancel_order(cancelled)

    assert ReportService().get_monthly_summary(y, m)["income"] == 500.0


def test_entries_outside_the_period_are_excluded(vehicle):
    _, y, m = _completed_order(vehicle, parts=0, charge=100)
    other_year = y - 1
    IncomeService().create_income("Año anterior", 999, date=f"{other_year}-{m:02d}-10")
    ExpenseService().create_expense("Año anterior", 999, date=f"{other_year}-{m:02d}-10")

    summary = ReportService().get_monthly_summary(y, m)
    assert summary["income"] == 100.0
    assert summary["expenses"] == 0.0


def test_quarterly_and_yearly_summaries(isolated_db):
    incomes, expenses = IncomeService(), ExpenseService()
    incomes.create_income("Enero", 100, date="2025-01-10")
    incomes.create_income("Marzo", 200, date="2025-03-31")
    incomes.create_income("Abril", 400, date="2025-04-01")
    expenses.create_expense("Febrero", 50, date="2025-02-01")
    expenses.create_expense("Diciembre", 25, date="2025-12-31")

    reports = ReportService()
    assert reports.get_summary_by_quarter(2025, 1) == {
        "income": 300.0, "expenses": 50.0, "profit": 250.0,
    }
    assert reports.get_summary_by_quarter(2025, 2)["income"] == 400.0
    assert reports.get_summary_by_quarter(2025, 4)["expenses"] == 25.0
    assert reports.get_summary_by_year(2025) == {
        "income": 700.0, "expenses": 75.0, "profit": 625.0,
    }


def test_ledgers_by_period_match_manual_totals(isolated_db):
    incomes, expenses = IncomeService(), ExpenseService()
    incomes.create_income("A", 100, date="2025-05-02")
    incomes.create_income("B", 50, date="2025-05-20")
    expenses.create_expense("C", 30, date="2025-05-03")

    assert [r["description"] for r in incomes.get_incomes_by_month(2025, 5)] == ["B", "A"]
    assert len(incomes.get_incomes_by_quarter(2025, 2)) == 2
    assert len(incomes.get_incomes_by_year(2025)) == 2
    assert len(expenses.get_expenses_by_month(2025, 5)) == 1
    assert len(expenses.get_expenses_by_quarter(2025, 2)) == 1
    assert len(expenses.get_expenses_by_year(2025)) == 1


@pytest.mark.parametrize(
    "period, value",
    [("monthly", 0), ("monthly", 13), ("monthly", None), ("quarterly", 5), ("weekly", 1)],
)
def test_invalid_period_raises(isolated_db, period, value):
    with pytest.raises(ValueError):
        ReportService().get_report_summary(period, 2025, value)


def test_negative_amounts_are_rejected_by_the_database(isolated_db):
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError):
        IncomeService().create_income("Negativo", -1, date="2025-01-01")
    with pytest.raises(sqlite3.IntegrityError):
        ExpenseService().create_expense("Negativo", -1, date="2025-01-01")


# --- B5: amounts are rounded to cents ---------------------------------------

def test_b5_zero_profit_is_exactly_zero(isolated_db):
    IncomeService().create_income("a", 0.1, date="2025-01-10")
    IncomeService().create_income("b", 0.2, date="2025-01-10")
    ExpenseService().create_expense("c", 0.3, date="2025-01-10")
    summary = ReportService().get_monthly_summary(2025, 1)
    assert summary == {"income": 0.3, "expenses": 0.3, "profit": 0.0}
    assert f"{summary['profit']:.2f}" == "0.00"  # never "-0.00"


def test_b5_amounts_are_stored_rounded(isolated_db):
    incomes, expenses = IncomeService(), ExpenseService()
    incomes.create_income("x", 10.006, date="2025-01-10")
    eid = expenses.create_expense("y", 3.333, date="2025-01-10")
    expenses.update_expense(eid, amount=4.444)
    assert incomes.get_incomes_by_month(2025, 1)[0]["amount"] == 10.01
    assert expenses.get_expenses_by_month(2025, 1)[0]["amount"] == 4.44


# --- B6: one source of truth for profit -------------------------------------

def test_b6_summary_and_order_profit_agree_even_with_items(vehicle):
    from services.order_item_service import OrderItemService

    orders = OrderService()
    oid = orders.create_order(vehicle)
    OrderItemService().create_item(oid, "Mano de obra", 100, 20)  # informational only
    orders.complete_order(oid, parts_cost=10, customer_charge=150)
    y, m, _ = completed_at(oid).split("-")

    reports = ReportService()
    assert reports.get_monthly_summary(int(y), int(m))["profit"] == 140.0
    assert reports.get_profit_per_order(oid) == 140.0
    assert reports.get_total_profit() == 140.0


def test_b6_profit_of_pending_or_cancelled_order_is_zero(vehicle):
    orders = OrderService()
    pending = orders.create_order(vehicle)
    cancelled = orders.create_order(vehicle)
    orders.cancel_order(cancelled)
    reports = ReportService()
    assert reports.get_profit_per_order(pending) == 0.0
    assert reports.get_profit_per_order(cancelled) == 0.0
    assert reports.get_total_profit() == 0.0


# --- B1: manual entries default to the local date ---------------------------

def test_b1_manual_entries_default_to_local_date(isolated_db, tz_where_local_date_differs_from_utc):
    from datetime import date

    IncomeService().create_income("hoy", 10)
    ExpenseService().create_expense("hoy", 5)
    today = date.today()
    assert len(IncomeService().get_incomes_by_month(today.year, today.month)) == 1
    assert IncomeService().get_incomes_by_month(today.year, today.month)[0]["date"] == today.isoformat()
    assert ExpenseService().get_expenses_by_month(today.year, today.month)[0]["date"] == today.isoformat()
