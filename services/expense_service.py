from database.connection import get_connection


class ExpenseService:

    def create_expense(self, description, amount, category=None, date=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO expenses (date, description, amount, category)
                VALUES (COALESCE(?, CURRENT_DATE), ?, ?, ?)
            """, (date, description, amount, category))

            expense_id = cursor.lastrowid

            conn.commit()

            return expense_id


    def update_expense(self, expense_id, description=None, amount=None, category=None, date=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE expenses
                SET description = COALESCE(?, description),
                    amount = COALESCE(?, amount),
                    category = COALESCE(?, category),
                    date = COALESCE(?, date)
                WHERE id = ?
            """, (description, amount, category, date, expense_id))

            if cursor.rowcount == 0:
                print("No expense found")

            conn.commit()


    def delete_expense(self, expense_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM expenses
                WHERE id = ?
            """, (expense_id,))

            if cursor.rowcount == 0:
                print("No expense found")

            conn.commit()


    def get_expense_by_id(self, expense_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM expenses
                WHERE id = ?
            """, (expense_id,))

            return cursor.fetchone()


    def get_all_expenses(self):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM expenses
                ORDER BY date DESC
            """)

            return cursor.fetchall()


    def get_expenses_by_date(self, date):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM expenses
                WHERE date = ?
                ORDER BY id DESC
            """, (date,))

            return cursor.fetchall()


    def get_expenses_by_month(self, year, month):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM expenses
                WHERE strftime('%Y', date) = ?
                AND strftime('%m', date) = ?
            """, (str(year), str(month).zfill(2)))

            return cursor.fetchall()

    def get_expenses_by_quarter(self, year, quarter):
        with get_connection() as conn:
            cursor = conn.cursor()
            qx = "(CAST(strftime('%m', date) AS INT) - 1) / 3 + 1"
            cursor.execute(
                f"""
                SELECT *
                FROM expenses
                WHERE strftime('%Y', date) = ?
                  AND {qx} = ?
                ORDER BY date DESC, id DESC
                """,
                (str(year), int(quarter)),
            )
            return cursor.fetchall()

    def get_expenses_by_year(self, year):
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT *
                FROM expenses
                WHERE strftime('%Y', date) = ?
                ORDER BY date DESC, id DESC
                """,
                (str(year),),
            )
            return cursor.fetchall()
