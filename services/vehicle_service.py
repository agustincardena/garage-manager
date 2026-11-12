import sqlite3

from database.connection import get_connection, transaction


def normalize_plate(plate) -> str | None:
    """Plates are stored trimmed and upper-case; empty means no plate."""
    return (plate or "").strip().upper() or None


class VehicleService:

    def assign_vehicle_to_client(
        self,
        vehicle_id: int,
        client_id: int,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        if not client_id:
            raise ValueError("errors.vehicle.invalid_client")
        with transaction(conn) as c:
            cursor = c.execute(
                "UPDATE vehicles SET client_id = ? WHERE id = ?",
                (client_id, vehicle_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.vehicle.not_found")

    def create_vehicle(
        self,
        client_id,
        brand=None,
        model=None,
        year=None,
        plate=None,
        notes=None,
        *,
        conn: sqlite3.Connection | None = None,
    ):
        plate_norm = normalize_plate(plate)
        with transaction(conn) as c:
            if plate_norm and self.get_vehicle_by_plate(plate_norm, conn=c):
                raise ValueError("errors.vehicle.duplicate_plate")
            cursor = c.execute(
                """
                INSERT INTO vehicles (client_id, brand, model, year, plate, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (client_id, brand, model, year, plate_norm, notes),
            )
            return cursor.lastrowid


    def update_vehicle(self, vehicle_id, brand=None, model=None, year=None, plate=None, notes=None):
        """Update the given fields (``None`` keeps the current value).

        The plate is normalized like on creation and must not belong to
        another vehicle (B7).
        """
        plate_norm = normalize_plate(plate)
        with transaction() as conn:
            if plate_norm:
                other = self.get_vehicle_by_plate(plate_norm, conn=conn)
                if other is not None and int(other["id"]) != int(vehicle_id):
                    raise ValueError("errors.vehicle.duplicate_plate")
            cursor = conn.execute(
                """
                UPDATE vehicles
                SET brand = COALESCE(?, brand),
                    model = COALESCE(?, model),
                    year = COALESCE(?, year),
                    plate = COALESCE(?, plate),
                    notes = COALESCE(?, notes)
                WHERE id = ?
                """,
                (brand, model, year, plate_norm, notes, vehicle_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.vehicle.not_found")


    def save_details(
        self,
        vehicle_id: int,
        *,
        brand: str | None,
        model: str | None,
        plate: str | None,
        notes: str | None,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Set the editable fields to exactly these values (empty clears).

        Unlike ``update_vehicle`` (where ``None`` keeps the current value), this
        is what an edit form needs. The plate is normalized and must be unique.
        """
        plate_norm = normalize_plate(plate)
        with transaction(conn) as c:
            if plate_norm:
                other = self.get_vehicle_by_plate(plate_norm, conn=c)
                if other is not None and int(other["id"]) != int(vehicle_id):
                    raise ValueError("errors.vehicle.duplicate_plate")
            cursor = c.execute(
                """
                UPDATE vehicles SET brand = ?, model = ?, plate = ?, notes = ?
                WHERE id = ?
                """,
                (
                    (brand or "").strip() or None,
                    (model or "").strip() or None,
                    plate_norm,
                    (notes or "").strip() or None,
                    vehicle_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.vehicle.not_found")

    def delete_vehicle(self, vehicle_id):
        """Delete a vehicle with no work orders or appointments.

        A vehicle with history cannot be deleted (its orders feed the reports).
        """
        with transaction() as conn:
            if self._has_history(conn, vehicle_id):
                raise ValueError("errors.vehicle.has_history")
            cursor = conn.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
            if cursor.rowcount == 0:
                raise ValueError("errors.vehicle.not_found")

    @staticmethod
    def _has_history(conn, vehicle_id) -> bool:
        for table in ("orders", "appointments"):
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE vehicle_id = ? LIMIT 1", (vehicle_id,)
            ).fetchone()
            if row is not None:
                return True
        return False

    def get_vehicle_by_id(self, vehicle_id, *, conn: sqlite3.Connection | None = None):
        with transaction(conn) as c:
            cursor = c.cursor()

            cursor.execute("""
                SELECT 
                    v.id,
                    v.client_id,
                    v.brand,
                    v.model,
                    v.year,
                    v.plate,
                    v.notes,
                    c.name AS client
                FROM vehicles v
                JOIN clients c ON v.client_id = c.id
                WHERE v.id = ?
            """, (vehicle_id,))

            return cursor.fetchone()


    def get_vehicles_by_client(self, client_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM vehicles
                WHERE client_id = ?
                ORDER BY id DESC
            """, (client_id,))

            return cursor.fetchall()


    def get_vehicle_by_plate(self, plate, *, conn: sqlite3.Connection | None = None):
        with transaction(conn) as c:
            return c.execute(
                """
                SELECT *
                FROM vehicles
                WHERE UPPER(TRIM(plate)) = UPPER(TRIM(?))
                """,
                (plate,),
            ).fetchone()


    def get_all_vehicles(self):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    v.id,
                    v.client_id,
                    v.plate,
                    v.brand,
                    v.model,
                    c.name AS client_name
                FROM vehicles v
                JOIN clients c ON v.client_id = c.id
                ORDER BY c.name COLLATE NOCASE, v.plate COLLATE NOCASE
            """)

            return cursor.fetchall()
