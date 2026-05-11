from database.connection import get_connection


class OrderService:
    """When closing with no line items, a single synthetic item is inserted for reporting."""

    _CLOSURE_ITEM_DESCRIPTION = "Order closure (full charge)"


    def create_order(self, vehicle_id, scheduled_date=None, scheduled_time=None, notes=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO orders (vehicle_id, status_id, scheduled_date, scheduled_time, notes)
                VALUES (?, 1, ?, ?, ?)
            """, (vehicle_id, scheduled_date, scheduled_time, notes))

            order_id = cursor.lastrowid

            conn.commit()

            return order_id


    def schedule_order(self, order_id, date, time):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE orders
                SET scheduled_date = ?, scheduled_time = ?, status_id = 2
                WHERE id = ?
            """, (date, time, order_id))
            if cursor.rowcount == 0:
                print("No order found")

            conn.commit()


    def start_order(self, order_id):
        with get_connection() as conn:
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


    def complete_order(
        self,
        order_id,
        parts_cost: float = 0.0,
        customer_charge: float = 0.0,
        completion_notes: str | None = None,
    ):
        if float(customer_charge) <= 0:
            raise ValueError("errors.order.charge_must_be_positive")
        if float(parts_cost) < 0:
            raise ValueError("errors.order.parts_cost_negative")

        parts = float(parts_cost)
        charge = float(customer_charge)
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM order_items WHERE order_id = ?",
                (order_id,),
            )
            existing_items = int(cursor.fetchone()[0])

            extra = (completion_notes or "").strip() or None
            cursor.execute(
                """
                UPDATE orders
                SET status_id = 5,
                    completed_at = CURRENT_DATE,
                    parts_cost = ?,
                    customer_charge = ?,
                    completion_notes = ?
                WHERE id = ? AND status_id NOT IN (5, 6)
                """,
                (parts, charge, extra, order_id),
            )
            if cursor.rowcount == 0:
                print("No order found")
            elif existing_items == 0:
                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, description, price, cost)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        self._CLOSURE_ITEM_DESCRIPTION,
                        charge,
                        parts,
                    ),
                )

            conn.commit()


    def cancel_order(self, order_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE orders
                SET status_id = 6
                WHERE id = ?
            """, (order_id,))
            if cursor.rowcount == 0:
                print("No order found")
            conn.commit()


    def get_order_by_id(self, order_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    o.id,
                    o.status_id,
                    o.scheduled_date,
                    o.scheduled_time,
                    o.created_at,
                    o.started_at,
                    o.completed_at,
                    o.notes,
                    o.parts_cost,
                    o.customer_charge,
                    o.completion_notes,
                    s.name AS status,
                    v.plate,
                    v.brand,
                    v.model,
                    c.name AS client
                FROM orders o
                JOIN order_status s ON o.status_id = s.id
                JOIN vehicles v ON o.vehicle_id = v.id
                JOIN clients c ON v.client_id = c.id
                WHERE o.id = ?
            """, (order_id,))

            return cursor.fetchone()


    def get_orders_by_date(self, date):
        with get_connection() as conn:
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

            return cursor.fetchall()


    def get_orders_by_status(self, status_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM orders
                WHERE status_id = ?
            """, (status_id,))

            return cursor.fetchall()


    def get_orders_by_vehicle(self, vehicle_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM orders
                WHERE vehicle_id = ?
                ORDER BY created_at DESC
            """, (vehicle_id,))

            return cursor.fetchall()
    
    def get_all_orders(self):
        with get_connection() as conn:
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

    def get_pending_workshop_orders(self):
        with get_connection() as conn:
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
                    o.notes,
                    c.name AS client
                FROM orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                JOIN clients c ON v.client_id = c.id
                WHERE o.status_id NOT IN (5, 6)
                ORDER BY o.created_at DESC
            """)

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "plate": row["plate"],
                    "brand": row["brand"],
                    "model": row["model"],
                    "status_id": row["status_id"],
                    "scheduled_date": row["scheduled_date"],
                    "scheduled_time": row["scheduled_time"],
                    "notes": row["notes"],
                    "client": row["client"],
                }
                for row in rows
            ]

    def get_history_orders(self, limit: int = 400):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    o.id,
                    o.completed_at,
                    v.plate,
                    v.brand,
                    v.model,
                    c.name AS client,
                    o.notes,
                    o.parts_cost,
                    o.customer_charge,
                    o.completion_notes
                FROM orders o
                JOIN vehicles v ON o.vehicle_id = v.id
                JOIN clients c ON v.client_id = c.id
                WHERE o.status_id = 5
                ORDER BY COALESCE(o.completed_at, o.created_at) DESC, o.id DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

            return [dict(row) for row in rows]
