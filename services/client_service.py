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


    def save_profile(
        self,
        client_id: int,
        *,
        name: str,
        phone: str | None,
        email: str | None,
        notes: str | None,
        vehicles: list[dict] | None = None,
    ) -> None:
        """F5: save a client's details and their vehicles' details in one go.

        Fields are set to exactly the given values (empty clears them; the name
        is required). Each item of ``vehicles`` has ``id``, ``brand``,
        ``model``, ``plate`` and ``notes`` and must belong to this client.
        If anything is invalid (e.g. a duplicate plate) nothing is saved.
        """
        from services.vehicle_service import VehicleService

        name = (name or "").strip()
        if not name:
            raise ValueError("errors.client.name_required")
        vehicle_service = VehicleService()
        with transaction() as conn:
            cursor = conn.execute(
                "UPDATE clients SET name = ?, phone = ?, email = ?, notes = ? WHERE id = ?",
                (
                    name,
                    (phone or "").strip() or None,
                    (email or "").strip() or None,
                    (notes or "").strip() or None,
                    client_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.client.not_found")
            for v in vehicles or []:
                owner = conn.execute(
                    "SELECT client_id FROM vehicles WHERE id = ?", (v["id"],)
                ).fetchone()
                if owner is None or int(owner[0]) != int(client_id):
                    raise ValueError("errors.vehicle.not_found")
                vehicle_service.save_details(
                    v["id"],
                    brand=v.get("brand"),
                    model=v.get("model"),
                    plate=v.get("plate"),
                    notes=v.get("notes"),
                    conn=conn,
                )

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
