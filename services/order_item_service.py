from database.connection import get_connection


class OrderItemService:

    def create_item(self, order_id, description, price, cost):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO order_items (order_id, description, price, cost)
                VALUES (?, ?, ?, ?)
            """, (order_id, description, price, cost))

            item_id = cursor.lastrowid

            conn.commit()

            return item_id


    def update_item(self, item_id, description=None, price=None, cost=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE order_items
                SET description = COALESCE(?, description),
                    price = COALESCE(?, price),
                    cost = COALESCE(?, cost)
                WHERE id = ?
            """, (description, price, cost, item_id))

            if cursor.rowcount == 0:
                print("No item found")

            conn.commit()


    def delete_item(self, item_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM order_items
                WHERE id = ?
            """, (item_id,))

            if cursor.rowcount == 0:
                print("No item found")

            conn.commit()


    def get_items_by_order(self, order_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    id,
                    description,
                    price,
                    cost,
                    (price - cost) AS profit
                FROM order_items
                WHERE order_id = ?
            """, (order_id,))

            return cursor.fetchall()


    def get_item_by_id(self, item_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT *
                FROM order_items
                WHERE id = ?
            """, (item_id,))

            return cursor.fetchone()
