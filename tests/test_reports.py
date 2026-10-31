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
