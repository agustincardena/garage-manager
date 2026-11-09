"""Known bugs from the improvement plan, written as the *expected* behaviour.

They are marked ``xfail(strict=True)``: they fail today, and the moment a fix
makes one pass, pytest reports it as XPASS -> error. When that happens, move the
test to the matching test file without the marker, as a regression test.

Codes (B7, B8c, ...) refer to the improvement plan. Fixed in phase 1 and moved
out of this file: B1, B3, B5, B6, B8a, B8b.
"""

from __future__ import annotations

import pytest

from services.client_service import ClientService
from services.vehicle_service import VehicleService


def _vehicle(plate: str = "AB123CD") -> tuple[int, int]:
    cid = ClientService().create_client("Ana")
    return cid, VehicleService().create_vehicle(cid, plate=plate)


@pytest.mark.xfail(strict=True, reason="B7: update_vehicle neither normalizes nor checks plates")
def test_b7_update_vehicle_rejects_duplicate_plate(isolated_db):
    cid, _ = _vehicle("AB123CD")
    other = VehicleService().create_vehicle(cid, plate="ZZ999ZZ")
    with pytest.raises(ValueError, match="errors.vehicle.duplicate_plate"):
        VehicleService().update_vehicle(other, plate="ab123cd")


@pytest.mark.xfail(strict=True, reason="B8c: deleting a client with vehicles raises a raw IntegrityError")
def test_b8c_delete_client_with_vehicles_raises_translated_error(isolated_db):
    cid, _ = _vehicle()
    with pytest.raises(ValueError, match="errors.client.has_vehicles"):
        ClientService().delete_client(cid)
