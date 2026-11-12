from database.connection import get_connection, transaction
from services import clock
from services.customer_resolution import check_parties, resolve_client_and_vehicle
from services.money import round_money
from services.order_status import CLOSED_STATUSES, OrderStatus


class OrderService:
    """Work orders. Flow: pending -> completed or cancelled.

    ``customer_charge`` and ``parts_cost`` of a completed order are the single
    source for its revenue and parts expense in every report.
    """

    def create_order(self, vehicle_id, scheduled_date=None, scheduled_time=None, notes=None):
        with transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO orders
                    (vehicle_id, status_id, created_at, scheduled_date, scheduled_time, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    vehicle_id,
                    OrderStatus.PENDING,
                    clock.today_iso(),
                    scheduled_date,
                    scheduled_time,
                    notes,
                ),
            )
            return cursor.lastrowid

    def create_walk_in_order(
        self,
        *,
        notes: str | None = None,
        client_id: int | None = None,
        new_client: dict | None = None,
        vehicle_id: int | None = None,
        new_vehicle: dict | None = None,
        reassign_vehicle: bool = False,
    ) -> int:
        """F3: open a pending order for a customer who arrives without an
        appointment, creating the client and/or vehicle if needed. All or
        nothing, like ``AppointmentService.save_booking``."""
        check_parties(
            client_id=client_id,
            new_client=new_client,
            vehicle_id=vehicle_id,
            new_vehicle=new_vehicle,
        )
        with transaction() as conn:
            _, vid = resolve_client_and_vehicle(
                conn,
                client_id=client_id,
                new_client=new_client,
                vehicle_id=vehicle_id,
                new_vehicle=new_vehicle,
                reassign_vehicle=reassign_vehicle,
            )
            cursor = conn.execute(
                """
                INSERT INTO orders (vehicle_id, status_id, created_at, notes)
                VALUES (?, ?, ?, ?)
                """,
                (vid, OrderStatus.PENDING, clock.today_iso(), (notes or "").strip() or None),
            )
            return int(cursor.lastrowid)

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

        parts = round_money(parts_cost)
        charge = round_money(customer_charge)
        extra = (completion_notes or "").strip() or None
        with transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET status_id = ?,
                    completed_at = ?,
                    parts_cost = ?,
                    customer_charge = ?,
                    completion_notes = ?
                WHERE id = ? AND status_id = ?
                """,
                (
                    OrderStatus.COMPLETED,
                    clock.today_iso(),
                    parts,
                    charge,
                    extra,
                    order_id,
                    OrderStatus.PENDING,
                ),
            )
            if cursor.rowcount == 0:
                self._raise_not_pending(conn, order_id)

    def correct_completed_order(
        self,
        order_id,
        parts_cost: float,
        customer_charge: float,
        completion_notes: str | None = None,
    ) -> None:
        """B4: fix the amounts/notes of a completed order. It stays completed
        and keeps its closing date, so it stays in the same report period."""
        if float(customer_charge) <= 0:
            raise ValueError("errors.order.charge_must_be_positive")
        if float(parts_cost) < 0:
            raise ValueError("errors.order.parts_cost_negative")
        with transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE orders
                SET parts_cost = ?, customer_charge = ?, completion_notes = ?
                WHERE id = ? AND status_id = ?
                """,
                (
                    round_money(parts_cost),
                    round_money(customer_charge),
                    (completion_notes or "").strip() or None,
                    order_id,
                    OrderStatus.COMPLETED,
                ),
            )
            if cursor.rowcount == 0:
                exists = conn.execute(
                    "SELECT 1 FROM orders WHERE id = ?", (order_id,)
                ).fetchone()
                raise ValueError(
                    "errors.order.not_completed" if exists else "errors.order.not_found"
                )

    def cancel_order(self, order_id):
        with transaction() as conn:
            cursor = conn.execute(
                "UPDATE orders SET status_id = ? WHERE id = ? AND status_id = ?",
                (OrderStatus.CANCELLED, order_id, OrderStatus.PENDING),
            )
            if cursor.rowcount == 0:
                self._raise_not_pending(conn, order_id)

    @staticmethod
    def _raise_not_pending(conn, order_id) -> None:
        row = conn.execute(
            "SELECT status_id FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row is None:
            raise ValueError("errors.order.not_found")
        raise ValueError("errors.order.not_pending")

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
                AND o.status_id != ?
                ORDER BY o.scheduled_time
            """, (date, OrderStatus.CANCELLED))

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
                WHERE o.status_id NOT IN (?, ?)
                ORDER BY o.created_at DESC
            """, CLOSED_STATUSES)

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
                WHERE o.status_id = ?
                ORDER BY COALESCE(o.completed_at, o.created_at) DESC, o.id DESC
                LIMIT ?
                """,
                (OrderStatus.COMPLETED, limit),
            )

            rows = cursor.fetchall()

            return [dict(row) for row in rows]
