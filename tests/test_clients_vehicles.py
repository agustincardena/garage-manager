"""Clients and vehicles: creation, search, plates and ownership."""

from __future__ import annotations

import pytest

from services.client_service import ClientService
from services.vehicle_service import VehicleService


def test_search_clients_matches_name_phone_and_email_case_insensitive(isolated_db):
    clients = ClientService()
    ana = clients.create_client("Ana Gómez", phone="3415551234", email="ana@mail.com")
    clients.create_client("Bruno Paz", phone="3410000000")

    assert [r["id"] for r in clients.search_clients("ana")] == [ana]
    assert [r["id"] for r in clients.search_clients("555")] == [ana]
    assert [r["id"] for r in clients.search_clients("MAIL.COM")] == [ana]
    assert len(clients.search_clients("")) == 2


def test_create_vehicle_normalizes_plate(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vid = vehicles.create_vehicle(cid, plate="  ab123cd ")
    assert vehicles.get_vehicle_by_id(vid)["plate"] == "AB123CD"
    assert vehicles.get_vehicle_by_plate("ab123cd")["id"] == vid


def test_create_vehicle_rejects_duplicate_plate_ignoring_case(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vehicles.create_vehicle(cid, plate="AB123CD")
    with pytest.raises(ValueError, match="errors.vehicle.duplicate_plate"):
        vehicles.create_vehicle(cid, plate="ab123cd")


def test_vehicle_without_plate_is_allowed(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vehicles.create_vehicle(cid, brand="Fiat")
    vehicles.create_vehicle(cid, brand="Renault")
    assert len(vehicles.get_vehicles_by_client(cid)) == 2


def test_assign_vehicle_to_client_changes_owner(isolated_db):
    clients = ClientService()
    ana, bruno = clients.create_client("Ana"), clients.create_client("Bruno")
    vehicles = VehicleService()
    vid = vehicles.create_vehicle(ana, plate="AB123CD")

    vehicles.assign_vehicle_to_client(vid, bruno)

    assert vehicles.get_vehicle_by_id(vid)["client_id"] == bruno
    assert vehicles.get_vehicles_by_client(ana) == []


@pytest.mark.parametrize("client_id", [None, 0])
def test_assign_vehicle_requires_client(isolated_db, client_id):
    cid = ClientService().create_client("Ana")
    vid = VehicleService().create_vehicle(cid, plate="AB123CD")
    with pytest.raises(ValueError, match="errors.vehicle.invalid_client"):
        VehicleService().assign_vehicle_to_client(vid, client_id)


def test_assign_unknown_vehicle_raises(isolated_db):
    cid = ClientService().create_client("Ana")
    with pytest.raises(ValueError, match="errors.vehicle.not_found"):
        VehicleService().assign_vehicle_to_client(9999, cid)


# --- B7: plates stay unique when editing --------------------------------------

def test_b7_update_vehicle_rejects_duplicate_plate_ignoring_case(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vehicles.create_vehicle(cid, plate="AB123CD")
    other = vehicles.create_vehicle(cid, plate="ZZ999ZZ")
    with pytest.raises(ValueError, match="errors.vehicle.duplicate_plate"):
        vehicles.update_vehicle(other, plate=" ab123cd ")
    assert vehicles.get_vehicle_by_id(other)["plate"] == "ZZ999ZZ"


def test_b7_update_vehicle_normalizes_and_allows_own_plate(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vid = vehicles.create_vehicle(cid, plate="AB123CD", brand="Ford")
    vehicles.update_vehicle(vid, plate="ab123cd", brand="Fiat")  # same plate, other case
    vehicles.update_vehicle(vid, plate=" ac456de ")
    row = vehicles.get_vehicle_by_id(vid)
    assert (row["plate"], row["brand"]) == ("AC456DE", "Fiat")


def test_b7_database_rejects_duplicate_plate_even_bypassing_services(isolated_db):
    import sqlite3

    from database.connection import get_connection

    cid = ClientService().create_client("Ana")
    VehicleService().create_vehicle(cid, plate="AB123CD")
    with get_connection() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO vehicles (client_id, plate) VALUES (?, 'ab123cd ')", (cid,))


def test_update_unknown_vehicle_raises(isolated_db):
    with pytest.raises(ValueError, match="errors.vehicle.not_found"):
        VehicleService().update_vehicle(9999, brand="X")


# --- B8c: deleting clients and vehicles never breaks history -----------------

def test_b8c_client_with_vehicles_cannot_be_deleted(isolated_db):
    cid = ClientService().create_client("Ana")
    VehicleService().create_vehicle(cid, plate="AB123CD")
    with pytest.raises(ValueError, match="errors.client.has_vehicles"):
        ClientService().delete_client(cid)
    assert ClientService().get_client_by_id(cid) is not None


def test_b8c_client_with_appointments_cannot_be_deleted(isolated_db):
    from database.connection import get_connection

    clients = ClientService()
    owner, other = clients.create_client("Ana"), clients.create_client("Beto")
    vid = VehicleService().create_vehicle(owner, plate="AB123CD")
    with get_connection() as conn:  # appointment of Beto with Ana's car
        conn.execute(
            "INSERT INTO appointments (client_id, vehicle_id, appointment_date, appointment_time)"
            " VALUES (?, ?, '2030-01-01', '09:00')",
            (other, vid),
        )
        conn.commit()
    with pytest.raises(ValueError, match="errors.client.has_appointments"):
        clients.delete_client(other)


def test_client_without_vehicles_can_be_deleted(isolated_db):
    clients = ClientService()
    cid = clients.create_client("Ana")
    clients.delete_client(cid)
    assert clients.get_client_by_id(cid) is None
    with pytest.raises(ValueError, match="errors.client.not_found"):
        clients.delete_client(cid)


def test_vehicle_with_orders_cannot_be_deleted(isolated_db):
    from services.order_service import OrderService

    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vid = vehicles.create_vehicle(cid, plate="AB123CD")
    OrderService().create_order(vid)
    with pytest.raises(ValueError, match="errors.vehicle.has_history"):
        vehicles.delete_vehicle(vid)
    assert vehicles.get_vehicle_by_id(vid) is not None


def test_vehicle_without_history_can_be_deleted(isolated_db):
    cid = ClientService().create_client("Ana")
    vehicles = VehicleService()
    vid = vehicles.create_vehicle(cid, plate="AB123CD")
    vehicles.delete_vehicle(vid)
    assert vehicles.get_vehicle_by_id(vid) is None
