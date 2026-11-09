from __future__ import annotations

import re
import sqlite3
from datetime import date

from database.connection import get_connection, transaction
from services import clock
from services.client_service import ClientService
from services.order_status import OrderStatus
from services.settings_service import SettingsService
from services.vehicle_service import VehicleService, normalize_plate


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
    if date.fromisoformat(ds) < clock.today():
        raise ValueError("errors.appointment.past_date")


def _iso(d: date | str) -> str:
    return d.isoformat() if isinstance(d, date) else str(d)


def _clean_reason(reason: str | None) -> str | None:
    return (reason or "").strip() or None


def _slot_changed(existing, ds: str, time_norm: str) -> bool:
    """Capacity is only checked when an appointment takes a (new) slot, so
    lowering the capacity never blocks editing appointments already booked."""
    if existing is None:
        return True
    return (str(existing["appointment_date"]), str(existing["appointment_time"])) != (
        ds,
        time_norm,
    )


def _assert_date_on_update(new_ds: str, previous_ds: str) -> None:
    if new_ds == previous_ds:
        return
    if date.fromisoformat(new_ds) < clock.today():
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
        *,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        """Raise if the slot already has as many appointments as the workshop
        allows at the same time (setting ``appointments.slot_capacity``)."""
        time_norm = _minutes_to_hhmm(_parse_time_to_minutes(time_str))
        with transaction(conn) as c:
            capacity = SettingsService().get_slot_capacity(conn=c)
            taken = c.execute(
                """
                SELECT COUNT(*) FROM appointments
                WHERE appointment_date = ? AND appointment_time = ?
                  AND id != COALESCE(?, -1)
                """,
                (_iso(appointment_date), time_norm, exclude_appointment_id),
            ).fetchone()[0]
        if taken >= capacity:
            raise ValueError("errors.appointment.slot_taken")

    def create_appointment(
        self,
        client_id: int,
        vehicle_id: int | None,
        date_val: date | str,
        time_str: str,
        reason: str | None = None,
        *,
        conn: sqlite3.Connection | None = None,
    ) -> int:
        if vehicle_id is None:
            raise ValueError("errors.appointment.requires_vehicle")
        ds = _iso(date_val)
        _assert_date_for_create(ds)
        time_norm = _minutes_to_hhmm(_parse_time_to_minutes(time_str))

        with transaction(conn) as c:
            self.assert_arrival_time_available(ds, time_norm, None, conn=c)
            cur = c.execute(
                """
                INSERT INTO appointments (
                    client_id, vehicle_id, appointment_date, appointment_time,
                    reason
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (client_id, vehicle_id, ds, time_norm, reason),
            )
            return int(cur.lastrowid)

    def save_booking(
        self,
        *,
        appointment_date: date | str,
        appointment_time: str,
        reason: str | None = None,
        appointment_id: int | None = None,
        client_id: int | None = None,
        new_client: dict | None = None,
        vehicle_id: int | None = None,
        new_vehicle: dict | None = None,
        reassign_vehicle: bool = False,
    ) -> int:
        """Create or edit an appointment, creating the client and/or vehicle if
        needed, as one all-or-nothing operation. Returns the appointment id.

        * Client: pass ``client_id`` or ``new_client`` (``name``, ``phone``).
        * Vehicle: pass ``vehicle_id`` or ``new_vehicle`` (``plate`` required,
          plus ``brand``, ``model``, ``notes``). A new vehicle whose plate already
          exists is treated as that existing vehicle.
        * If the vehicle belongs to another client it is only moved to this
          client when ``reassign_vehicle`` is True; otherwise nothing is saved.
        * An empty ``reason`` clears it.

        If any step fails (slot full, duplicate data, invalid date...), nothing
        is written: no orphan client, vehicle or appointment is left behind.
        """
        if (client_id is None) == (new_client is None):
            raise ValueError("errors.booking.client_required")
        if (vehicle_id is None) == (new_vehicle is None):
            raise ValueError("errors.appointment.requires_vehicle")

        ds = _iso(appointment_date)
        time_norm = _minutes_to_hhmm(_parse_time_to_minutes(appointment_time))
        reason_clean = _clean_reason(reason)

        clients, vehicles = ClientService(), VehicleService()
        with transaction() as conn:
            existing = None
            if appointment_id is not None:
                existing = conn.execute(
                    "SELECT appointment_date, appointment_time FROM appointments WHERE id = ?",
                    (appointment_id,),
                ).fetchone()
                if existing is None:
                    raise ValueError("errors.appointment.not_found")
                _assert_date_on_update(ds, str(existing["appointment_date"]))
            else:
                _assert_date_for_create(ds)
            if _slot_changed(existing, ds, time_norm):
                self.assert_arrival_time_available(ds, time_norm, appointment_id, conn=conn)

            if new_client is not None:
                client_id = clients.create_client(
                    name=new_client.get("name"),
                    phone=(new_client.get("phone") or "").strip() or None,
                    conn=conn,
                )

            if new_vehicle is not None:
                plate = normalize_plate(new_vehicle.get("plate"))
                if not plate:
                    raise ValueError("errors.vehicle.plate_required")
                found = vehicles.get_vehicle_by_plate(plate, conn=conn)
                if found is not None:
                    vehicle_id = int(found["id"])
                else:
                    vehicle_id = vehicles.create_vehicle(
                        client_id,
                        brand=(new_vehicle.get("brand") or "").strip() or None,
                        model=(new_vehicle.get("model") or "").strip() or None,
                        plate=plate,
                        notes=(new_vehicle.get("notes") or "").strip() or None,
                        conn=conn,
                    )

            vehicle = vehicles.get_vehicle_by_id(vehicle_id, conn=conn)
            if vehicle is None:
                raise ValueError("errors.vehicle.not_found")
            if int(vehicle["client_id"]) != int(client_id):
                if not reassign_vehicle:
                    raise ValueError("errors.vehicle.belongs_to_other_client")
                vehicles.assign_vehicle_to_client(vehicle_id, client_id, conn=conn)

            if existing is None:
                cur = conn.execute(
                    """
                    INSERT INTO appointments
                        (client_id, vehicle_id, appointment_date, appointment_time, reason)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (client_id, vehicle_id, ds, time_norm, reason_clean),
                )
                return int(cur.lastrowid)

            conn.execute(
                """
                UPDATE appointments
                SET client_id = ?, vehicle_id = ?, appointment_date = ?,
                    appointment_time = ?, reason = ?
                WHERE id = ?
                """,
                (client_id, vehicle_id, ds, time_norm, reason_clean, appointment_id),
            )
            return int(appointment_id)

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

        if _slot_changed(existing, ds, time_norm):
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

    def convert_to_order(self, appointment_id: int) -> int:
        """Create a pending work order from an appointment and remove the
        appointment. The order keeps the appointment's date and time."""
        with transaction() as conn:
            appt = conn.execute(
                "SELECT * FROM appointments WHERE id = ?", (appointment_id,)
            ).fetchone()
            if appt is None:
                raise ValueError("errors.appointment.not_found")
            row = dict(appt)
            if row.get("vehicle_id") is None:
                raise ValueError("errors.appointment.requires_vehicle")

            note_parts = [
                f"Appointment: {row.get('appointment_date')} {row.get('appointment_time')}",
            ]
            if row.get("reason"):
                note_parts.append(str(row["reason"]))
            notes = " · ".join(note_parts)

            cursor = conn.execute(
                """
                INSERT INTO orders (
                    vehicle_id, status_id, notes, created_at,
                    scheduled_date, scheduled_time
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row["vehicle_id"],
                    OrderStatus.PENDING,
                    notes,
                    clock.today_iso(),
                    row.get("appointment_date"),
                    row.get("appointment_time"),
                ),
            )
            new_order_id = int(cursor.lastrowid)
            conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
            return new_order_id
