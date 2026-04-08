from database.connection import get_connection


class ReportService:

    def _connect(self):
        return get_connection()


    def get_income_by_month(self, year, month):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(oi.price), 0)
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status_id = 5
            AND strftime('%Y', o.completed_at) = ?
            AND strftime('%m', o.completed_at) = ?
        """, (str(year), str(month).zfill(2)))

        result = cursor.fetchone()[0]
        conn.close()

        return result


    def get_expenses_by_month(self, year, month):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE strftime('%Y', date) = ?
            AND strftime('%m', date) = ?
        """, (str(year), str(month).zfill(2)))

        result = cursor.fetchone()[0]
        conn.close()

        return result


    def get_profit_by_month(self, year, month):
        income = self.get_income_by_month(year, month)
        expenses = self.get_expenses_by_month(year, month)

        return income - expenses


    def get_profit_per_order(self, order_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(price - cost), 0)
            FROM order_items
            WHERE order_id = ?
        """, (order_id,))

        result = cursor.fetchone()[0]
        conn.close()

        return result


    def get_monthly_summary(self, year, month):
        income = self.get_income_by_month(year, month)
        expenses = self.get_expenses_by_month(year, month)
        profit = income - expenses

        return {
            "income": income,
            "expenses": expenses,
            "profit": profit
        }


    def get_total_profit(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(oi.price - oi.cost), 0)
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status_id = 5
        """)

        result = cursor.fetchone()[0]
        conn.close()

        return result