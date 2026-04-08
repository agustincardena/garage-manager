from database.connection import get_connection


class OrderService:

    def _connect(self):
        return get_connection()


    def create_order(self, vehicle_id, scheduled_date=None, scheduled_time=None, notes=None):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO orders (vehicle_id, status_id, scheduled_date, scheduled_time, notes)
            VALUES (?, 1, ?, ?, ?)
        """, (vehicle_id, scheduled_date, scheduled_time, notes))

        order_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return order_id


    def schedule_order(self, order_id, date, time):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE orders
            SET scheduled_date = ?, scheduled_time = ?, status_id = 2
            WHERE id = ?
        """, (date, time, order_id))
        if cursor.rowcount == 0:
            print("No order found")

        conn.commit()
        conn.close()


    def start_order(self, order_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE orders
            SET status_id = 3,
                started_at = CURRENT_DATE
            WHERE id = ?
        """, (order_id,))
        if cursor.rowcount == 0:
            print("No order found")

        conn.commit()
        conn.close()


    def complete_order(self, order_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE orders
            SET status_id = 5,
                completed_at = CURRENT_DATE
            WHERE id = ?
        """, (order_id,))
        if cursor.rowcount == 0:
            print("No order found")

        conn.commit()
        conn.close()


    def cancel_order(self, order_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE orders
            SET status_id = 6
            WHERE id = ?
        """, (order_id,))
        if cursor.rowcount == 0:
            print("No order found")
        conn.commit()
        conn.close()


    def get_order_by_id(self, order_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                o.id,
                o.scheduled_date,
                o.scheduled_time,
                o.created_at,
                o.started_at,
                o.completed_at,
                o.notes,
                s.name AS status,
                v.brand,
                v.model,
                c.name AS client
            FROM orders o
            JOIN order_status s ON o.status_id = s.id
            JOIN vehicles v ON o.vehicle_id = v.id
            JOIN clients c ON v.client_id = c.id
            WHERE o.id = ?
        """, (order_id,))

        result = cursor.fetchone()
        conn.close()

        return result


    def get_orders_by_date(self, date):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                o.id,
                o.scheduled_time,
                s.name AS status,
                v.brand,
                v.model,
                c.name AS client
            FROM orders o
            JOIN vehicles v ON o.vehicle_id = v.id
            JOIN clients c ON v.client_id = c.id
            JOIN order_status s ON o.status_id = s.id
            WHERE o.scheduled_date = ?
            AND o.status_id != 6
            ORDER BY o.scheduled_time
        """, (date,))

        results = cursor.fetchall()
        conn.close()

        return results


    def get_orders_by_status(self, status_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM orders
            WHERE status_id = ?
        """, (status_id,))

        results = cursor.fetchall()
        conn.close()

        return results


    def get_orders_by_vehicle(self, vehicle_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM orders
            WHERE vehicle_id = ?
            ORDER BY created_at DESC
        """, (vehicle_id,))

        results = cursor.fetchall()
        conn.close()

        return results
    
    def get_all_orders(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
            o.id,
            v.plate,
            v.brand,
            v.model,
            o.status_id,
            o.scheduled_date,
            o.scheduled_time,
            o.notes
        FROM orders o
        JOIN vehicles v ON o.vehicle_id = v.id
        ORDER BY o.created_at DESC
    """)

        rows = cursor.fetchall()
        conn.close()

        orders = []
        for row in rows:
                orders.append({
            "id": row[0],
            "plate": row[1],
            "brand": row[2],
            "model": row[3],
            "status_id": row[4],
            "scheduled_date": row[5],
            "scheduled_time": row[6],
            "notes": row[7]
        })

        return orders