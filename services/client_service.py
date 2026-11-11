import sqlite3

from database.connection import get_connection, transaction
from services import clock


class ClientService:

    def create_client(
        self,
        name,
        phone=None,
        email=None,
        notes=None,
        *,
        conn: sqlite3.Connection | None = None,
    ):
        name = (name or "").strip()
        if not name:
            raise ValueError("errors.client.name_required")
        with transaction(conn) as c:
            cursor = c.execute(
                """
                INSERT INTO clients (name, phone, email, notes, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, phone, email, notes, clock.today_iso()),
            )
            return cursor.lastrowid


    def update_client(self, client_id, name=None, phone=None, email=None, notes=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE clients
                SET name = COALESCE(?, name),
                    phone = COALESCE(?, phone),
                    email = COALESCE(?, email),
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (name, phone, email, notes, client_id))

            if cursor.rowcount == 0:
                raise ValueError("errors.client.not_found")

            conn.commit()


    def delete_client(self, client_id):
        """Delete a client with no vehicles or appointments (B8c).

        Vehicles must be transferred or deleted first, so no history is lost.
        """
        with transaction() as conn:
            for table, error_key in (
                ("vehicles", "errors.client.has_vehicles"),
                ("appointments", "errors.client.has_appointments"),
            ):
                row = conn.execute(
                    f"SELECT 1 FROM {table} WHERE client_id = ? LIMIT 1", (client_id,)
                ).fetchone()
                if row is not None:
                    raise ValueError(error_key)
            cursor = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            if cursor.rowcount == 0:
                raise ValueError("errors.client.not_found")


    def get_client_by_id(self, client_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM clients
                WHERE id = ?
            """, (client_id,))

            return cursor.fetchone()


    def get_all_clients(self):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM clients
                ORDER BY created_at DESC
            """)

            return cursor.fetchall()

    def search_clients(self, query: str, limit: int = 80):
        with get_connection() as conn:
            cursor = conn.cursor()
            q = (query or "").strip()
            if not q:
                cursor.execute(
                    """
                    SELECT * FROM clients
                    ORDER BY name COLLATE NOCASE
                    LIMIT ?
                    """,
                    (limit,),
                )
            else:
                like = f"%{q}%"
                cursor.execute(
                    """
                    SELECT * FROM clients
                    WHERE name COLLATE NOCASE LIKE ?
                       OR IFNULL(phone, '') COLLATE NOCASE LIKE ?
                       OR IFNULL(email, '') COLLATE NOCASE LIKE ?
                    ORDER BY name COLLATE NOCASE
                    LIMIT ?
                    """,
                    (like, like, like, limit),
                )
            rows = cursor.fetchall()
            return list(rows)
