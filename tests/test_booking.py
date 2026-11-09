"""AppointmentService.save_booking: all-or-nothing appointment booking (B2, B8a)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from database.connection import get_connection
from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.vehicle_service import VehicleService


def _counts() -> dict[str, int]:
    with get_connection() as conn:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("clients", "vehicles", "appointments")
        }


NEW_CLIENT = {"name": "Beto Paz", "phone": "3415550000"}
NEW_VEHICLE = {"plate": " bb222bb ", "brand": "Fiat", "model": "Uno", "notes": ""}


@pytest.fixture
def ana(isolated_db):
    cid = ClientService().create_client("Ana", phone="341")
    vid = VehicleService().create_vehicle(cid, plate="AA111AA")
    return cid, vid


def test_new_client_and_vehicle_are_created_with_the_appointment(isolated_db, future_date):
    aid = AppointmentService().save_booking(
        appointment_date=future_date,
        appointment_time="9:00",
        reason="  Service  ",
        new_client=NEW_CLIENT,
        new_vehicle=NEW_VEHICLE,
    )
    row = AppointmentService().get_appointment_by_id(aid)
    assert row["client_name"] == "Beto Paz"
    assert row["plate"] == "BB222BB"
    assert row["appointment_time"] == "09:00"
    assert row["reason"] == "Service"
    assert _counts() == {"clients": 1, "vehicles": 1, "appointments": 1}


def test_full_slot_leaves_no_orphan_client_or_vehicle(ana, future_date):
    """B2: before, the client (and vehicle) were saved even if the slot was taken,
    and retrying created duplicates."""
    cid, vid = ana
    AppointmentService().create_appointment(cid, vid, future_date, "09:00")
    before = _counts()

    for _ in range(2):  # retrying must not accumulate duplicates either
        with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
            AppointmentService().save_booking(
                appointment_date=future_date,
                appointment_time="09:00",
                new_client=NEW_CLIENT,
                new_vehicle=NEW_VEHICLE,
            )
    assert _counts() == before


def test_past_date_leaves_nothing(isolated_db):
    yesterday = date.today() - timedelta(days=1)
    with pytest.raises(ValueError, match="errors.appointment.past_date"):
        AppointmentService().save_booking(
            appointment_date=yesterday,
            appointment_time="09:00",
            new_client=NEW_CLIENT,
            new_vehicle=NEW_VEHICLE,
        )
    assert _counts() == {"clients": 0, "vehicles": 0, "appointments": 0}


def test_existing_plate_of_other_client_requires_confirmation(ana, future_date):
    _, vid = ana
    before = _counts()
    with pytest.raises(ValueError, match="errors.vehicle.belongs_to_other_client"):
        AppointmentService().save_booking(
            appointment_date=future_date,
            appointment_time="09:00",
            new_client=NEW_CLIENT,
            new_vehicle={"plate": "aa111aa"},
        )
    assert _counts() == before
    assert VehicleService().get_vehicle_by_id(vid)["client"] == "Ana"


def test_confirmed_reassignment_moves_vehicle_in_same_operation(ana, future_date):
    _, vid = ana
    aid = AppointmentService().save_booking(
        appointment_date=future_date,
        appointment_time="09:00",
        new_client=NEW_CLIENT,
        new_vehicle={"plate": "aa111aa"},
        reassign_vehicle=True,
    )
    row = AppointmentService().get_appointment_by_id(aid)
    assert row["vehicle_id"] == vid
    assert VehicleService().get_vehicle_by_id(vid)["client"] == "Beto Paz"
    assert _counts()["vehicles"] == 1


def test_reassignment_is_rolled_back_if_slot_is_full(ana, future_date):
    cid, vid = ana
    other = ClientService().create_client("Carla")
    AppointmentService().create_appointment(cid, vid, future_date, "09:00")
    with pytest.raises(ValueError, match="errors.appointment.slot_taken"):
        AppointmentService().save_booking(
            appointment_date=future_date,
            appointment_time="09:00",
            client_id=other,
            vehicle_id=vid,
            reassign_vehicle=True,
        )
    assert VehicleService().get_vehicle_by_id(vid)["client_id"] == cid


def test_missing_plate_for_new_vehicle(isolated_db, future_date):
    with pytest.raises(ValueError, match="errors.vehicle.plate_required"):
        AppointmentService().save_booking(
            appointment_date=future_date,
            appointment_time="09:00",
            new_client=NEW_CLIENT,
            new_vehicle={"plate": "  "},
        )
    assert _counts()["clients"] == 0


@pytest.mark.parametrize(
    "kwargs, error_key",
    [
        ({}, "errors.booking.client_required"),
        ({"client_id": 1, "new_client": NEW_CLIENT}, "errors.booking.client_required"),
        ({"client_id": 1}, "errors.appointment.requires_vehicle"),
    ],
)
def test_client_and_vehicle_must_be_given_exactly_once(ana, future_date, kwargs, error_key):
    with pytest.raises(ValueError, match=error_key):
        AppointmentService().save_booking(
            appointment_date=future_date, appointment_time="09:00", **kwargs
        )


def test_new_client_requires_name(isolated_db, future_date):
    with pytest.raises(ValueError, match="errors.client.name_required"):
        AppointmentService().save_booking(
            appointment_date=future_date,
            appointment_time="09:00",
            new_client={"name": "  ", "phone": "1"},
            new_vehicle=NEW_VEHICLE,
        )
    assert _counts() == {"clients": 0, "vehicles": 0, "appointments": 0}


# --- editing ---------------------------------------------------------------

def test_edit_moves_time_keeps_own_slot_and_clears_reason(ana, future_date):
    """B8a: an empty reason now clears it (the dialog used to send None = keep)."""
    cid, vid = ana
    appts = AppointmentService()
    aid = appts.create_appointment(cid, vid, future_date, "09:00", reason="Ruido")

    same = appts.save_booking(
        appointment_id=aid,
        appointment_date=future_date,
        appointment_time="09:00",
        reason="",
        client_id=cid,
        vehicle_id=vid,
    )
    assert same == aid
    assert appts.get_appointment_by_id(aid)["reason"] is None

    appts.save_booking(
        appointment_id=aid,
        appointment_date=future_date,
        appointment_time="11:30",
        reason="Frenos",
        client_id=cid,
        vehicle_id=vid,
    )
    row = appts.get_appointment_by_id(aid)
    assert (row["appointment_time"], row["reason"]) == ("11:30", "Frenos")
    assert _counts()["appointments"] == 1


def test_edit_of_past_appointment_keeping_its_date_is_allowed(ana):
    cid, vid = ana
    past = (date.today() - timedelta(days=2)).isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO appointments (client_id, vehicle_id, appointment_date, appointment_time)"
            " VALUES (?, ?, ?, '09:00')",
            (cid, vid, past),
        )
        conn.commit()
        aid = conn.execute("SELECT MAX(id) FROM appointments").fetchone()[0]
    AppointmentService().save_booking(
        appointment_id=aid,
        appointment_date=past,
        appointment_time="10:00",
        client_id=cid,
        vehicle_id=vid,
    )
    assert AppointmentService().get_appointment_by_id(aid)["appointment_time"] == "10:00"


def test_edit_unknown_appointment(ana, future_date):
    cid, vid = ana
    with pytest.raises(ValueError, match="errors.appointment.not_found"):
        AppointmentService().save_booking(
            appointment_id=9999,
            appointment_date=future_date,
            appointment_time="09:00",
            client_id=cid,
            vehicle_id=vid,
        )
