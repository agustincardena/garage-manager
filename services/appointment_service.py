import re
from datetime import date

from database.connection import get_connection


def _parse_time_to_minutes(value: str) -> int:
    if not value or not str(value).strip():
        raise ValueError("errors.appointment.invalid_time_empty")
    s = str(value).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", s)
    if not m:
        raise ValueError("errors.appointment.invalid_time_format")
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        raise ValueError("errors.appointment.invalid_time_values")
    return h * 60 + mi


def _minutes_to_hhmm(total: int) -> str:
    total = total % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _assert_date_for_create(ds: str) -> None:
    if date.fromisoformat(ds) < date.today():
        raise ValueError("errors.appointment.past_date")


def _assert_date_on_update(new_ds: str, previous_ds: str) -> None:
    if new_ds == previous_ds:
        return
    if date.fromisoformat(new_ds) < date.today():
        raise ValueError("errors.appointment.past_date")


class AppointmentService:

    def _row_to_dict(self, row) -> dict:
        return dict(row) if row is not None else None

    def get_appointment_by_id(self, appointment_id: int) -> dict | None:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    a.id,
                    a.client_id,
                    a.vehicle_id,
                    a.appointment_date,
                    a.appointment_time,
                    a.reason,
                    a.status,
                    c.name AS client_name,
                    v.plate,
                    v.brand,
                    v.model
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                LEFT JOIN vehicles v ON a.vehicle_id = v.id
                WHERE a.id = ?
                """,
                (appointment_id,),
            )
            row = cur.fetchone()
            return self._row_to_dict(row)

    def get_appointments_by_date(self, d: date | str) -> list[dict]:
        if isinstance(d, date):
            ds = d.isoformat()
        else:
            ds = str(d)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    a.id,
                    a.appointment_date,
                    a.appointment_time,
                    c.name AS client_name,
                    v.plate,
                    v.brand,
                    v.model,
                    a.reason,
                    a.client_id,
                    a.vehicle_id
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                LEFT JOIN vehicles v ON a.vehicle_id = v.id
                WHERE a.appointment_date = ?
                ORDER BY a.appointment_time ASC
                """,
                (ds,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def get_appointments_between(self, start: date | str, end: date | str) -> list[dict]:
        if isinstance(start, date):
            start_s = start.isoformat()
        else:
            start_s = str(start)
        if isinstance(end, date):
            end_s = end.isoformat()
        else:
            end_s = str(end)
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT
                    a.id,
                    a.appointment_date,
                    a.appointment_time,
                    c.name AS client_name,
                    v.plate,
                    v.brand,
                    v.model,
                    a.reason,
                    a.client_id,
                    a.vehicle_id
                FROM appointments a
                JOIN clients c ON a.client_id = c.id
                LEFT JOIN vehicles v ON a.vehicle_id = v.id
                WHERE a.appointment_date >= ? AND a.appointment_date <= ?
                ORDER BY a.appointment_date ASC, a.appointment_time ASC
                """,
                (start_s, end_s),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def assert_arrival_time_available(
        self,
        appointment_date: str,
        time_str: str,
        exclude_appointment_id: int | None = None,
    ) -> None:
        time_norm = _minutes_to_hhmm(_parse_time_to_minutes(time_str))
        with get_connection() as conn:
            cur = conn.cursor()
            if exclude_appointment_id is None:
                cur.execute(
                    """
                    SELECT id FROM appointments
                    WHERE appointment_date = ? AND appointment_time = ?
                    LIMIT 1
                    """,
                    (appointment_date, time_norm),
                )
            else:
                cur.execute(
                    """
                    SELECT id FROM appointments
                    WHERE appointment_date = ? AND appointment_time = ?
                      AND id != ?
                    LIMIT 1
                    """,
                    (appointment_date, time_norm, exclude_appointment_id),
                )
            if cur.fetchone() is not None:
                raise ValueError("errors.appointment.slot_taken")

    def create_appointment(
        self,
        client_id: int,
        vehicle_id: int | None,
        date_val: date | str,
        time_str: str,
        reason: str | None = None,
    ) -> int:
        if vehicle_id is None:
            raise ValueError("errors.appointment.requires_vehicle")
        if isinstance(date_val, date):
            ds = date_val.isoformat()
        else:
            ds = str(date_val)
        _assert_date_for_create(ds)
        time_norm = _minutes_to_hhmm(_parse_time_to_minutes(time_str))
        self.assert_arrival_time_available(ds, time_norm, None)

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO appointments (
                    client_id, vehicle_id, appointment_date, appointment_time,
                    reason
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_id, vehicle_id, ds, time_norm, reason),
            )
            new_id = int(cur.lastrowid)
            conn.commit()
            return new_id

    def update_appointment(
        self,
        appointment_id: int,
        *,
        client_id: int | None = None,
        vehicle_id: int | None = None,
        appointment_date: date | str | None = None,
        appointment_time: str | None = None,
        reason: str | None = None,
    ) -> bool:
        existing = self.get_appointment_by_id(appointment_id)
        if not existing:
            return False

        new_client = client_id if client_id is not None else existing["client_id"]
        new_vehicle = (
            vehicle_id if vehicle_id is not None else existing["vehicle_id"]
        )
        if new_vehicle is None:
            raise ValueError("errors.appointment.requires_vehicle")

        if appointment_date is None:
            ds = existing["appointment_date"]
        elif isinstance(appointment_date, date):
            ds = appointment_date.isoformat()
        else:
            ds = str(appointment_date)

        prev_ds = str(existing["appointment_date"])
        _assert_date_on_update(ds, prev_ds)

        if appointment_time is not None:
            time_norm = _minutes_to_hhmm(_parse_time_to_minutes(appointment_time))
        else:
            time_norm = existing["appointment_time"]

        self.assert_arrival_time_available(ds, time_norm, appointment_id)

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE appointments
                SET client_id = ?,
                    vehicle_id = ?,
                    appointment_date = ?,
                    appointment_time = ?,
                    reason = COALESCE(?, reason)
                WHERE id = ?
                """,
                (new_client, new_vehicle, ds, time_norm, reason, appointment_id),
            )
            ok = cur.rowcount > 0
            conn.commit()
            return ok

    def delete_appointment(self, appointment_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
            count = cursor.rowcount
            conn.commit()
            return count > 0

    def convert_to_order(self, appointment_id: int) -> int | None:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
                appt = cursor.fetchone()
                if not appt:
                    return None
                row = dict(appt)
                if row.get("vehicle_id") is None:
                    print("Error: appointment has no linked vehicle")
                    return None

                note_parts = [
                    f"Appointment: {row.get('appointment_date')} {row.get('appointment_time')}",
                ]
                if row.get("reason"):
                    note_parts.append(str(row["reason"]))
                notes = " · ".join(note_parts)

                cursor.execute(
                    """
                    INSERT INTO orders (vehicle_id, status_id, notes, created_at)
                    VALUES (?, 1, ?, CURRENT_DATE)
                    """,
                    (row["vehicle_id"], notes),
                )
                new_order_id = int(cursor.lastrowid)
                cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
                conn.commit()
                return new_order_id
            except Exception as e:
                conn.rollback()
                print(f"Error converting appointment to order: {e}")
                return None
