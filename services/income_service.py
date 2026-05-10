from database.connection import get_connection


class IncomeService:

    def create_income(self, description, amount, category=None, date=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO incomes (date, description, amount, category)
                VALUES (COALESCE(?, CURRENT_DATE), ?, ?, ?)
            """, (date, description, amount, category))

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
