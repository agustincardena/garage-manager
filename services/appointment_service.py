from database.connection import get_connection

class AppointmentService:

    def _connect(self):
        return get_connection()

    def create_appointment(self, client_id, vehicle_id, date, time, reason=None):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO appointments (client_id, vehicle_id, appointment_date, appointment_time, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (client_id, vehicle_id, date, time, reason))

        appointment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return appointment_id

    def delete_appointment(self, appointment_id):
        """Elimina el turno (si el cliente no vino o se canceló)."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count > 0

    def get_appointments_by_date(self, date):
        """Para la visualización de la agenda del taller."""
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                a.id,
                a.appointment_time,
                c.name AS client_name,
                v.plate,
                v.brand,
                v.model,
                a.reason
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            LEFT JOIN vehicles v ON a.vehicle_id = v.id
            WHERE a.appointment_date = ?
            ORDER BY a.appointment_time ASC
        """, (date,))

        results = cursor.fetchall()
        conn.close()
        return results

    def convert_to_order(self, appointment_id):
        """
        Transforma un turno en una orden de trabajo real.
        Crea la orden y elimina el turno de la agenda.
        """
        conn = self._connect()
        cursor = conn.cursor()

        try:
            # 1. Obtener datos del turno
            cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
            appt = cursor.fetchone()
            
            if not appt or appt[2] is None:
                print("Error: El turno no tiene vehiculo asociado")
                return None

            # 2. Insertar en la tabla orders (status_id 1 = pending)
            # Usamos los datos que ya tenemos del turno
            cursor.execute("""
                INSERT INTO orders (vehicle_id, status_id, notes, created_at)
                VALUES (?, 1, ?, CURRENT_DATE)
            """, (appt[2], f"Turno previo: {appt[3]}"))
            
            new_order_id = cursor.lastrowid

            # 3. Borrar el turno de la agenda (limpieza)
            cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))

            conn.commit()
            return new_order_id
            
        except Exception as e:
            conn.rollback()
            print(f"Error al convertir turno a orden: {e}")
            return None
        finally:
            conn.close()