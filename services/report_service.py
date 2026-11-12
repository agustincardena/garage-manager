from __future__ import annotations

from database.connection import get_connection
from services.money import round_money
from services.order_status import OrderStatus


# SQLite quarter from calendar month (1–12) → 1–4; integer division (Q1=Jan–Mar).
_QUARTER_EXPR = "(CAST(strftime('%m', {col}) AS INT) - 1) / 3 + 1"


_COMPLETED = int(OrderStatus.COMPLETED)


class ReportService:
    """Aggregates revenue (completed orders + manual incomes) and expenses.

    Single source of truth: a completed order contributes its
    ``customer_charge`` to income and its ``parts_cost`` to expenses.
    ``order_items`` are informational and never summed into reports.
    All returned amounts are rounded to cents.
    """

    @staticmethod
    def _row_float(row) -> float:
        v = row[0] if row is not None else None
        if v is None:
            return 0.0
        return float(v)

    def _sum_completed_order_charges(
        self, cursor, where_sql: str, params: tuple
    ) -> float:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(CAST(o.customer_charge AS REAL)), 0)
            FROM orders o
            WHERE o.status_id = {_COMPLETED} AND ({where_sql})
            """,
            params,
        )
        return self._row_float(cursor.fetchone())

    def _sum_completed_order_parts(
        self, cursor, where_sql: str, params: tuple
    ) -> float:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(CAST(o.parts_cost AS REAL)), 0)
            FROM orders o
            WHERE o.status_id = {_COMPLETED} AND ({where_sql})
            """,
            params,
        )
        return self._row_float(cursor.fetchone())

    def _sum_manual_incomes(
        self, cursor, where_sql: str, params: tuple
    ) -> float:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(CAST(amount AS REAL)), 0)
            FROM incomes
            WHERE ({where_sql})
            """,
            params,
        )
        return self._row_float(cursor.fetchone())

    def _sum_expenses(self, cursor, where_sql: str, params: tuple) -> float:
        cursor.execute(
            f"""
            SELECT COALESCE(SUM(CAST(amount AS REAL)), 0)
            FROM expenses
            WHERE ({where_sql})
            """,
            params,
        )
        return self._row_float(cursor.fetchone())

    def _total_expenses(
        self, cursor, order_where: str, order_params: tuple, expense_where: str, expense_params: tuple
    ) -> float:
        manual = self._sum_expenses(cursor, expense_where, expense_params)
        from_order_parts = self._sum_completed_order_parts(cursor, order_where, order_params)
        return round_money(manual + from_order_parts)

    def _total_income(
        self,
        cursor,
        order_where: str,
        order_params: tuple,
        income_where: str,
        income_params: tuple,
    ) -> float:
        from_orders = self._sum_completed_order_charges(cursor, order_where, order_params)
        manual = self._sum_manual_incomes(cursor, income_where, income_params)
        return round_money(from_orders + manual)

    def _period_filters(
        self, period_type: str, year: int, value: int | None
    ) -> tuple[str, tuple, str, tuple, str, tuple]:
        """
        Build WHERE fragments and params for orders (completed_at), incomes (date),
        and expenses (date). Returns:
        (order_where, order_params, income_where, income_params, expense_where, expense_params)
        """
        y = str(year)
        pt = period_type.lower()

        if pt == "monthly":
            if value is None or not (1 <= int(value) <= 12):
                raise ValueError("monthly period requires value in 1..12 (month)")
            m = str(int(value)).zfill(2)
            order_w = (
                "strftime('%Y', o.completed_at) = ? "
                "AND strftime('%m', o.completed_at) = ?"
            )
            order_p = (y, m)
            date_w = "strftime('%Y', date) = ? AND strftime('%m', date) = ?"
            date_p = (y, m)
            return order_w, order_p, date_w, date_p, date_w, date_p

        if pt == "quarterly":
            if value is None or not (1 <= int(value) <= 4):
                raise ValueError("quarterly period requires value in 1..4 (quarter)")
            q = int(value)
            qx_o = _QUARTER_EXPR.format(col="o.completed_at")
            qx_d = _QUARTER_EXPR.format(col="date")
            order_w = f"strftime('%Y', o.completed_at) = ? AND {qx_o} = ?"
            order_p = (y, q)
            date_w = f"strftime('%Y', date) = ? AND {qx_d} = ?"
            date_p = (y, q)
            return order_w, order_p, date_w, date_p, date_w, date_p

        if pt == "yearly":
            order_w = "strftime('%Y', o.completed_at) = ?"
            order_p = (y,)
            date_w = "strftime('%Y', date) = ?"
            date_p = (y,)
            return order_w, order_p, date_w, date_p, date_w, date_p

        raise ValueError(
            f"period_type must be 'monthly', 'quarterly', or 'yearly', got {period_type!r}"
        )

    def _income_for_period(
        self, period_type: str, year: int, value: int | None
    ) -> float:
        ow, op, iw, ip, _, _ = self._period_filters(period_type, year, value)
        with get_connection() as conn:
            cur = conn.cursor()
            return self._total_income(cur, ow, op, iw, ip)

    def _expenses_for_period(
        self, period_type: str, year: int, value: int | None
    ) -> float:
        ow, op, _, _, ew, ep = self._period_filters(period_type, year, value)
        with get_connection() as conn:
            cur = conn.cursor()
            return self._total_expenses(cur, ow, op, ew, ep)

    # --- Public: by granularity (all return float totals) ---

    def get_income_by_month(self, year, month) -> float:
        return self._income_for_period("monthly", int(year), int(month))

    def get_expenses_by_month(self, year, month) -> float:
        return self._expenses_for_period("monthly", int(year), int(month))

    def get_income_by_quarter(self, year, quarter) -> float:
        return self._income_for_period("quarterly", int(year), int(quarter))

    def get_expenses_by_quarter(self, year, quarter) -> float:
        return self._expenses_for_period("quarterly", int(year), int(quarter))

    def get_income_by_year(self, year) -> float:
        return self._income_for_period("yearly", int(year), None)

    def get_expenses_by_year(self, year) -> float:
        return self._expenses_for_period("yearly", int(year), None)

    def get_profit_by_month(self, year, month) -> float:
        return round_money(
            self.get_income_by_month(year, month) - self.get_expenses_by_month(year, month)
        )

    def get_report_summary(
        self, period_type: str, year: int, value: int | None = None
    ) -> dict[str, float]:
        """
        Unified totals for income, expenses, and profit.

        period_type:
          - 'monthly': value = month (1–12)
          - 'quarterly': value = quarter (1–4)
          - 'yearly': value ignored
        """
        ow, op, iw, ip, ew, ep = self._period_filters(
            period_type, int(year), value
        )
        with get_connection() as conn:
            cur = conn.cursor()
            income = self._total_income(cur, ow, op, iw, ip)
            expenses = self._total_expenses(cur, ow, op, ew, ep)
        return {
            "income": income,
            "expenses": expenses,
            "profit": round_money(income - expenses),
        }

    def get_monthly_summary(self, year, month) -> dict[str, float]:
        """Backward-compatible wrapper around get_report_summary('monthly', ...)."""
        return self.get_report_summary("monthly", year, month)

    def get_summary_by_quarter(self, year: int, quarter: int) -> dict[str, float]:
        """Totals for calendar quarter (1–4), same logic as monthly (orders + incomes / expenses)."""
        return self.get_report_summary("quarterly", int(year), int(quarter))

    def get_summary_by_year(self, year: int) -> dict[str, float]:
        """Totals for calendar year, same logic as monthly."""
        return self.get_report_summary("yearly", int(year), None)

    def get_completed_orders_for_period(
        self, period_type: str, year: int, value: int | None = None
    ) -> list[dict]:
        """F4: completed orders behind the period's order income and parts
        expense, newest first, so the ledgers add up to the totals."""
        order_where, order_params, *_ = self._period_filters(period_type, int(year), value)
        with get_connection() as conn:
            rows = conn.execute(
                f"""
                SELECT o.id, o.completed_at, v.plate, c.name AS client,
                       COALESCE(o.customer_charge, 0) AS customer_charge,
                       COALESCE(o.parts_cost, 0) AS parts_cost
                FROM orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                JOIN clients c ON v.client_id = c.id
                WHERE o.status_id = {_COMPLETED} AND ({order_where})
                ORDER BY o.completed_at DESC, o.id DESC
                """,
                order_params,
            ).fetchall()
        return [
            {
                **dict(r),
                "customer_charge": round_money(r["customer_charge"]),
                "parts_cost": round_money(r["parts_cost"]),
            }
            for r in rows
        ]

    def get_profit_per_order(self, order_id) -> float:
        """Charge minus parts cost of a completed order; 0 for any other status."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COALESCE(customer_charge, 0) - COALESCE(parts_cost, 0)
                FROM orders
                WHERE id = ? AND status_id = {_COMPLETED}
                """,
                (order_id,),
            )
            return round_money(self._row_float(cursor.fetchone()))

    def get_total_profit(self) -> float:
        """All-time charge minus parts cost of completed orders (manual incomes
        and expenses are not included; use the period summaries for that)."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COALESCE(SUM(COALESCE(customer_charge, 0) - COALESCE(parts_cost, 0)), 0)
                FROM orders
                WHERE status_id = {_COMPLETED}
                """
            )
            return round_money(self._row_float(cursor.fetchone()))
