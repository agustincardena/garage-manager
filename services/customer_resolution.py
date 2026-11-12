"""Shared step for operations that pick or create a client and a vehicle
(booking an appointment, opening a walk-in work order).

Everything runs on the caller's connection, so it is part of the caller's
transaction: if a later step fails, the new client/vehicle are rolled back too.
"""

from __future__ import annotations

import sqlite3

from services.client_service import ClientService
from services.vehicle_service import VehicleService, normalize_plate


def check_parties(
    *,
    client_id: int | None,
    new_client: dict | None,
    vehicle_id: int | None,
    new_vehicle: dict | None,
) -> None:
    """Exactly one of client_id/new_client and of vehicle_id/new_vehicle."""
    if (client_id is None) == (new_client is None):
        raise ValueError("errors.booking.client_required")
    if (vehicle_id is None) == (new_vehicle is None):
        raise ValueError("errors.appointment.requires_vehicle")


def resolve_client_and_vehicle(
    conn: sqlite3.Connection,
    *,
    client_id: int | None = None,
    new_client: dict | None = None,
    vehicle_id: int | None = None,
    new_vehicle: dict | None = None,
    reassign_vehicle: bool = False,
) -> tuple[int, int]:
    """Return ``(client_id, vehicle_id)``, creating them if needed.

    * Client: ``client_id`` or ``new_client`` (``name``, ``phone``).
    * Vehicle: ``vehicle_id`` or ``new_vehicle`` (``plate`` required, plus
      ``brand``, ``model``, ``notes``). A new vehicle whose plate already exists
      is treated as that existing vehicle.
    * A vehicle of another client is moved only if ``reassign_vehicle``;
      otherwise ``errors.vehicle.belongs_to_other_client`` is raised.
    """
    check_parties(
        client_id=client_id,
        new_client=new_client,
        vehicle_id=vehicle_id,
        new_vehicle=new_vehicle,
    )
    clients, vehicles = ClientService(), VehicleService()

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
    return int(client_id), int(vehicle_id)
