from database.connection import get_connection


class VehicleService:

    def assign_vehicle_to_client(self, vehicle_id: int, client_id: int) -> None:
        if not client_id:
            raise ValueError("errors.vehicle.invalid_client")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE vehicles SET client_id = ? WHERE id = ?",
                (client_id, vehicle_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("errors.vehicle.not_found")
            conn.commit()

    def create_vehicle(self, client_id, brand=None, model=None, year=None, plate=None, notes=None):
        plate_norm = (plate or "").strip().upper() or None
        if plate_norm and self.get_vehicle_by_plate(plate_norm):
            raise ValueError("errors.vehicle.duplicate_plate")

        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO vehicles (client_id, brand, model, year, plate, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (client_id, brand, model, year, plate_norm, notes))

            vehicle_id = cursor.lastrowid

            conn.commit()

            return vehicle_id


    def update_vehicle(self, vehicle_id, brand=None, model=None, year=None, plate=None, notes=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE vehicles
                SET brand = COALESCE(?, brand),
                    model = COALESCE(?, model),
                    year = COALESCE(?, year),
                    plate = COALESCE(?, plate),
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (brand, model, year, plate, notes, vehicle_id))

            if cursor.rowcount == 0:
                print("No vehicle found")

            conn.commit()


    def delete_vehicle(self, vehicle_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM vehicles
                WHERE id = ?
            """, (vehicle_id,))

            if cursor.rowcount == 0:
                print("No vehicle found")

            conn.commit()


    def get_vehicle_by_id(self, vehicle_id):
        with get_connection() as conn:
            cursor = conn.cursor()

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


    def get_vehicle_by_plate(self, plate):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM vehicles
                WHERE UPPER(TRIM(plate)) = UPPER(TRIM(?))
            """, (plate,))

            return cursor.fetchone()


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
