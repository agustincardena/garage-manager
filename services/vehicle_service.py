from database.connection import get_connection


class VehicleService:

    def _connect(self):
        return get_connection()


    def create_vehicle(self, client_id, brand=None, model=None, year=None, plate=None, notes=None):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO vehicles (client_id, brand, model, year, plate, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (client_id, brand, model, year, plate, notes))

        vehicle_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return vehicle_id


    def update_vehicle(self, vehicle_id, brand=None, model=None, year=None, plate=None, notes=None):
        conn = self._connect()
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
        conn.close()


    def delete_vehicle(self, vehicle_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM vehicles
            WHERE id = ?
        """, (vehicle_id,))

        if cursor.rowcount == 0:
            print("No vehicle found")

        conn.commit()
        conn.close()


    def get_vehicle_by_id(self, vehicle_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                v.id,
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

        result = cursor.fetchone()
        conn.close()

        return result


    def get_vehicles_by_client(self, client_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM vehicles
            WHERE client_id = ?
            ORDER BY id DESC
        """, (client_id,))

        results = cursor.fetchall()
        conn.close()

        return results


    def get_vehicle_by_plate(self, plate):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM vehicles
            WHERE plate = ?
        """, (plate,))

        result = cursor.fetchone()
        conn.close()

        return result