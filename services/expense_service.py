from database.connection import get_connection


class ExpenseService:

    def _connect(self):
        return get_connection()


    def create_expense(self, description, amount, category=None, date=None):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO expenses (date, description, amount, category)
            VALUES (COALESCE(?, CURRENT_DATE), ?, ?, ?)
        """, (date, description, amount, category))

        expense_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return expense_id


    def update_expense(self, expense_id, description=None, amount=None, category=None, date=None):
        conn = self._connect()
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
        conn.close()


    def delete_expense(self, expense_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM expenses
            WHERE id = ?
        """, (expense_id,))

        if cursor.rowcount == 0:
            print("No expense found")

        conn.commit()
        conn.close()


    def get_expense_by_id(self, expense_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM expenses
            WHERE id = ?
        """, (expense_id,))

        result = cursor.fetchone()
        conn.close()

        return result


    def get_all_expenses(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM expenses
            ORDER BY date DESC
        """)

        results = cursor.fetchall()
        conn.close()

        return results


    def get_expenses_by_date(self, date):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM expenses
            WHERE date = ?
            ORDER BY id DESC
        """, (date,))

        results = cursor.fetchall()
        conn.close()

        return results


    def get_expenses_by_month(self, year, month):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM expenses
            WHERE strftime('%Y', date) = ?
            AND strftime('%m', date) = ?
        """, (str(year), str(month).zfill(2)))

        results = cursor.fetchall()
        conn.close()

        return results