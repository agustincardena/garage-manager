from database.connection import get_connection


class ClientService:

    def create_client(self, name, phone=None, email=None, notes=None):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO clients (name, phone, email, notes)
                VALUES (?, ?, ?, ?)
            """, (name, phone, email, notes))

            client_id = cursor.lastrowid

            conn.commit()

            return client_id


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
                print("No client found")

            conn.commit()


    def delete_client(self, client_id):
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM clients
                WHERE id = ?
            """, (client_id,))

            if cursor.rowcount == 0:
                print("No client found")

            conn.commit()


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
