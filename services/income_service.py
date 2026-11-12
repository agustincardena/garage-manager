from database.connection import get_connection
from services import clock
from services.money import round_money


class IncomeService:

    def create_income(self, description, amount, category=None, date=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO incomes (date, description, amount, category)
                VALUES (?, ?, ?, ?)
            """, (date or clock.today_iso(), description, round_money(amount), category))

            income_id = cursor.lastrowid

            conn.commit()

            return income_id

    def get_incomes_by_month(self, year, month):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM incomes
                WHERE strftime('%Y', date) = ?
                AND strftime('%m', date) = ?
                ORDER BY date DESC, id DESC
            """, (str(year), str(month).zfill(2)))

            return cursor.fetchall()

    def get_incomes_by_quarter(self, year, quarter):
        with get_connection() as conn:
            cursor = conn.cursor()
            qx = "(CAST(strftime('%m', date) AS INT) - 1) / 3 + 1"
            cursor.execute(
                f"""
                SELECT *
                FROM incomes
                WHERE strftime('%Y', date) = ?
                  AND {qx} = ?
                ORDER BY date DESC, id DESC
                """,
                (str(year), int(quarter)),
            )
            return cursor.fetchall()

    def get_incomes_by_year(self, year):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM incomes
                WHERE strftime('%Y', date) = ?
                ORDER BY date DESC, id DESC
                """,
                (str(year),),
            )
            return cursor.fetchall()

    def update_income(self, income_id, description=None, amount=None, category=None, date=None):
        """Update the given fields (``None`` keeps the current value)."""
        if description is not None and not description.strip():
            raise ValueError("errors.income.description_required")
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE incomes
                SET description = COALESCE(?, description),
                    amount = COALESCE(?, amount),
                    category = COALESCE(?, category),
                    date = COALESCE(?, date)
                WHERE id = ?
                """,
                (
                    None if description is None else description.strip(),
                    None if amount is None else round_money(amount),
                    category,
                    date,
                    income_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.income.not_found")
            conn.commit()

    def delete_income(self, income_id):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM incomes WHERE id = ?", (income_id,))
            if cursor.rowcount == 0:
                raise ValueError("errors.income.not_found")
            conn.commit()
