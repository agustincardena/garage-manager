from database.connection import get_connection


class ClientService:

    def _connect(self):
        return get_connection()


    def create_client(self, name, phone=None, email=None, notes=None):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO clients (name, phone, email, notes)
            VALUES (?, ?, ?, ?)
        """, (name, phone, email, notes))

        client_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return client_id


    def update_client(self, client_id, name=None, phone=None, email=None, notes=None):
        conn = self._connect()
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
        conn.close()


    def delete_client(self, client_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM clients
            WHERE id = ?
        """, (client_id,))

        if cursor.rowcount == 0:
            print("No client found")

        conn.commit()
        conn.close()


    def get_client_by_id(self, client_id):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM clients
            WHERE id = ?
        """, (client_id,))

        result = cursor.fetchone()
        conn.close()

        return result


    def get_all_clients(self):
        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM clients
            ORDER BY created_at DESC
        """)

        results = cursor.fetchall()
        conn.close()

        return results