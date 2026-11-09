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
