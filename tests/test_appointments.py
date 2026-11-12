"""Appointments: validation, time slots, editing and conversion to work orders."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.order_service import OrderService
from services.vehicle_service import VehicleService


@pytest.fixture
def client_vehicle(isolated_db):
    cid = ClientService().create_client("Ana", phone="341")
    vid = VehicleService().create_vehicle(cid, brand="Ford", model="Ka", plate="AB123CD")
    return cid, vid


def test_create_appointment_normalizes_time(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "9:05", reason="Service")
    row = appts.get_appointment_by_id(aid)
    assert row["appointment_time"] == "09:05"
    assert row["appointment_date"] == future_date
    assert row["reason"] == "Service"
    assert row["plate"] == "AB123CD"


def test_create_appointment_accepts_today(client_vehicle):
    cid, vid = client_vehicle
    aid = AppointmentService().create_appointment(cid, vid, date.today(), "23:59")
    assert aid > 0


def test_create_appointment_rejects_past_date(client_vehicle):
    cid, vid = client_vehicle
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValueError, match="errors.appointment.past_date"):
        AppointmentService().create_appointment(cid, vid, yesterday, "10:00")


@pytest.mark.parametrize(
    "time_str, error_key",
    [
        ("", "errors.appointment.invalid_time_empty"),
        ("   ", "errors.appointment.invalid_time_empty"),
        ("10", "errors.appointment.invalid_time_format"),
        ("10:5", "errors.appointment.invalid_time_format"),
        ("diez", "errors.appointment.invalid_time_format"),
        ("24:00", "errors.appointment.invalid_time_values"),
        ("10:60", "errors.appointment.invalid_time_values"),
    ],
)
def test_create_appointment_rejects_invalid_time(
    client_vehicle, future_date, time_str, error_key
):
    cid, vid = client_vehicle
    with pytest.raises(ValueError, match=error_key):
        AppointmentService().create_appointment(cid, vid, future_date, time_str)


def test_create_appointment_requires_vehicle(client_vehicle, future_date):
    cid, _ = client_vehicle
    with pytest.raises(ValueError, match="errors.appointment.requires_vehicle"):
        AppointmentService().create_appointment(cid, None, future_date, "10:00")


def test_same_slot_is_rejected_even_with_different_time_format(client_vehicle, future_date):
    """Default capacity is one appointment per exact date + time."""
    cid, vid = client_vehicle
    appts = AppointmentService()
    appts.create_appointment(cid, vid, future_date, "09:00")
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        appts.create_appointment(cid, vid, future_date, "9:00")
    appts.create_appointment(cid, vid, future_date, "09:30")


def test_slot_capacity_allows_several_cars_at_the_same_time(client_vehicle, future_date):
    from services.settings_service import SettingsService

    cid, vid = client_vehicle
    SettingsService().set_slot_capacity(2)
    appts = AppointmentService()
    appts.create_appointment(cid, vid, future_date, "09:00")
    appts.create_appointment(cid, vid, future_date, "09:00")
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        appts.create_appointment(cid, vid, future_date, "09:00")
    assert len(appts.get_appointments_by_date(future_date)) == 2


def test_lowering_capacity_keeps_existing_appointments(client_vehicle, future_date):
    from services.settings_service import SettingsService

    cid, vid = client_vehicle
    SettingsService().set_slot_capacity(3)
    appts = AppointmentService()
    ids = [appts.create_appointment(cid, vid, future_date, "09:00") for _ in range(3)]
    SettingsService().set_slot_capacity(1)
    assert len(appts.get_appointments_by_date(future_date)) == 3
    # Editing without changing the slot is allowed even if it is over capacity...
    assert appts.update_appointment(ids[0], reason="x") is True
    # ...but moving another appointment into the full slot is not.
    other = appts.create_appointment(cid, vid, future_date, "10:00")
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        appts.update_appointment(other, appointment_time="09:00")


def test_update_keeps_own_slot_and_moves_time(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00")

    assert appts.update_appointment(aid, reason="Frenos") is True
    assert appts.update_appointment(aid, appointment_time="11:15") is True

    row = appts.get_appointment_by_id(aid)
    assert row["appointment_time"] == "11:15"
    assert row["reason"] == "Frenos"


def test_update_cannot_take_another_slot(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    appts.create_appointment(cid, vid, future_date, "09:00")
    other = appts.create_appointment(cid, vid, future_date, "10:00")
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        appts.update_appointment(other, appointment_time="09:00")


def test_update_cannot_move_to_past(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="errors.appointment.past_date"):
        appts.update_appointment(aid, appointment_date=yesterday)


def test_update_unknown_appointment_returns_false(isolated_db):
    assert AppointmentService().update_appointment(9999, reason="x") is False


def test_listings_are_sorted_by_date_and_time(client_vehicle):
    cid, vid = client_vehicle
    appts = AppointmentService()
    d1 = date.today() + timedelta(days=1)
    d2 = date.today() + timedelta(days=2)
    appts.create_appointment(cid, vid, d2, "08:00")
    appts.create_appointment(cid, vid, d1, "15:00")
    appts.create_appointment(cid, vid, d1, "09:00")

    day = appts.get_appointments_by_date(d1)
    assert [r["appointment_time"] for r in day] == ["09:00", "15:00"]

    between = appts.get_appointments_between(d1, d2)
    assert [(r["appointment_date"], r["appointment_time"]) for r in between] == [
        (d1.isoformat(), "09:00"),
        (d1.isoformat(), "15:00"),
        (d2.isoformat(), "08:00"),
    ]


def test_delete_appointment(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00")
    assert appts.delete_appointment(aid) is True
    assert appts.delete_appointment(aid) is False
    assert appts.get_appointment_by_id(aid) is None


def test_convert_to_order_creates_pending_order(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00", reason="Ruido en frenos")

    oid = appts.convert_to_order(aid)

    order = OrderService().get_order_by_id(oid)
    assert order["status_id"] == 1
    assert order["plate"] == "AB123CD"
    assert "Ruido en frenos" in order["notes"]
    assert future_date in order["notes"]
    assert order["created_at"] == date.today().isoformat()
    # The appointment is kept as history, marked and linked to the order.
    appt = appts.get_appointment_by_id(aid)
    assert (appt["status"], appt["order_id"]) == ("in_workshop", oid)
    assert [r["status"] for r in appts.get_appointments_by_date(future_date)] == ["in_workshop"]


@pytest.fixture
def converted(client_vehicle, future_date):
    cid, vid = client_vehicle
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00", reason="Frenos")
    oid = appts.convert_to_order(aid)
    return cid, vid, aid, oid


def test_appointment_in_workshop_cannot_be_converted_again(converted):
    _, _, aid, _ = converted
    with pytest.raises(ValueError, match="errors.appointment.in_workshop"):
        AppointmentService().convert_to_order(aid)
    assert len(OrderService().get_all_orders()) == 1


def test_appointment_in_workshop_cannot_be_edited_or_deleted(converted, future_date):
    cid, vid, aid, _ = converted
    appts = AppointmentService()
    with pytest.raises(ValueError, match="errors.appointment.in_workshop"):
        appts.update_appointment(aid, reason="otro")
    with pytest.raises(ValueError, match="errors.appointment.in_workshop"):
        appts.save_booking(
            appointment_id=aid,
            appointment_date=future_date,
            appointment_time="10:00",
            client_id=cid,
            vehicle_id=vid,
        )
    with pytest.raises(ValueError, match="errors.appointment.in_workshop"):
        appts.delete_appointment(aid)
    assert appts.get_appointment_by_id(aid)["reason"] == "Frenos"


def test_appointment_in_workshop_still_uses_its_slot(converted, future_date):
    cid, vid, _, _ = converted
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        AppointmentService().create_appointment(cid, vid, future_date, "09:00")


def test_b8b_converted_order_keeps_schedule(client_vehicle, future_date):
    cid, vid = client_vehicle
    aid = AppointmentService().create_appointment(cid, vid, future_date, "10:00")
    oid = AppointmentService().convert_to_order(aid)
    order = OrderService().get_order_by_id(oid)
    assert (order["scheduled_date"], order["scheduled_time"]) == (future_date, "10:00")


def test_convert_unknown_appointment_raises(isolated_db):
    with pytest.raises(ValueError, match="errors.appointment.not_found"):
        AppointmentService().convert_to_order(9999)
