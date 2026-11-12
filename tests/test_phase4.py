"""Phase 4: language preference (U1), formats (U2) and no-show appointments (U4)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from database.connection import get_connection
from services import clock
from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.settings_service import SettingsService, resolve_language
from services.vehicle_service import VehicleService
from ui.formatting import format_date, format_money, qt_date_format


# --- U2: formats --------------------------------------------------------------

@pytest.mark.parametrize(
    "value, es, en",
    [
        (1234.56, "$ 1.234,56", "$1,234.56"),
        (0, "$ 0,00", "$0.00"),
        (-0.0000001, "$ 0,00", "$0.00"),  # never "-0,00"
        (1234567.891, "$ 1.234.567,89", "$1,234,567.89"),
        (-50.5, "-$ 50,50", "-$50.50"),
        ("12.3", "$ 12,30", "$12.30"),
        (None, "$ —", "$ —"),
        ("abc", "$ —", "$ —"),
    ],
)
def test_format_money(value, es, en):
    assert format_money(value, "es") == es
    assert format_money(value, "en") == en


@pytest.mark.parametrize(
    "value, es, en",
    [
        ("2026-10-31", "31/10/2026", "10/31/2026"),
        ("2026-01-05 09:30", "05/01/2026", "01/05/2026"),
        (date(2026, 3, 7), "07/03/2026", "03/07/2026"),
        (None, "—", "—"),
        ("", "—", "—"),
        ("no es fecha", "no es fecha", "no es fecha"),
    ],
)
def test_format_date(value, es, en):
    assert format_date(value, "es") == es
    assert format_date(value, "en") == en


def test_qt_date_format_matches_format_date():
    assert qt_date_format("es") == "dd/MM/yyyy"
    assert qt_date_format("en") == "MM/dd/yyyy"


# --- U1: language ---------------------------------------------------------------

@pytest.mark.parametrize(
    "saved, system, expected",
    [
        ("en", "es_AR", "en"),  # the user's choice wins
        ("es", "en_US", "es"),
        (None, "es_AR", "es"),
        (None, "en_US", "en"),
        (None, "pt_BR", "es"),  # unsupported system language -> Spanish
        (None, None, "es"),
        ("fr", "en_GB", "en"),  # invalid saved value is ignored
    ],
)
def test_resolve_language(saved, system, expected):
    assert resolve_language(saved, system) == expected


def test_language_is_saved_in_the_database(isolated_db):
    settings = SettingsService()
    assert settings.get_language() is None
    settings.set_language("en")
    assert SettingsService().get_language() == "en"
    settings.set_language("es")
    assert settings.get_language() == "es"
    with pytest.raises(ValueError, match="errors.settings.language_unsupported"):
        settings.set_language("fr")
    assert settings.get_language() == "es"


# --- U4: no-show ------------------------------------------------------------------

@pytest.fixture
def ana(isolated_db):
    cid = ClientService().create_client("Ana")
    vid = VehicleService().create_vehicle(cid, plate="AA111AA")
    return cid, vid


def _past_appointment(cid, vid, days_ago=1, time="09:00") -> int:
    day = (date.today() - timedelta(days=days_ago)).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO appointments (client_id, vehicle_id, appointment_date, appointment_time)"
            " VALUES (?, ?, ?, ?)",
            (cid, vid, day, time),
        )
        conn.commit()
        return cur.lastrowid


def test_past_appointment_can_be_marked_and_unmarked(ana):
    cid, vid = ana
    appts = AppointmentService()
    aid = _past_appointment(cid, vid)

    appts.mark_no_show(aid)
    assert appts.get_appointment_by_id(aid)["status"] == "no_show"
    day = (date.today() - timedelta(days=1)).isoformat()
    assert [r["status"] for r in appts.get_appointments_by_date(day)] == ["no_show"]

    appts.unmark_no_show(aid)
    assert appts.get_appointment_by_id(aid)["status"] == "scheduled"


def test_no_show_is_read_only_history(ana):
    cid, vid = ana
    appts = AppointmentService()
    aid = _past_appointment(cid, vid)
    appts.mark_no_show(aid)
    for action in (
        lambda: appts.convert_to_order(aid),
        lambda: appts.update_appointment(aid, reason="x"),
        lambda: appts.delete_appointment(aid),
        lambda: appts.mark_no_show(aid),
    ):
        with pytest.raises(ValueError, match="errors.appointment.no_show"):
            action()


def test_future_appointment_cannot_be_marked(ana, future_date):
    cid, vid = ana
    aid = AppointmentService().create_appointment(cid, vid, future_date, "09:00")
    with pytest.raises(ValueError, match="errors.appointment.not_expired"):
        AppointmentService().mark_no_show(aid)


def test_today_counts_as_past_only_after_its_time(ana, monkeypatch):
    cid, vid = ana
    appts = AppointmentService()
    today = date.today()
    monkeypatch.setattr(clock, "now", lambda: datetime(today.year, today.month, today.day, 10, 0))
    earlier = _past_appointment(cid, vid, days_ago=0, time="09:30")
    later = _past_appointment(cid, vid, days_ago=0, time="10:30")
    appts.mark_no_show(earlier)
    with pytest.raises(ValueError, match="errors.appointment.not_expired"):
        appts.mark_no_show(later)


def test_in_workshop_appointment_cannot_be_marked_no_show(ana):
    cid, vid = ana
    appts = AppointmentService()
    aid = _past_appointment(cid, vid)
    appts.convert_to_order(aid)
    with pytest.raises(ValueError, match="errors.appointment.in_workshop"):
        appts.mark_no_show(aid)
    with pytest.raises(ValueError, match="errors.appointment.not_no_show"):
        appts.unmark_no_show(aid)


def test_unknown_appointment(isolated_db):
    with pytest.raises(ValueError, match="errors.appointment.not_found"):
        AppointmentService().mark_no_show(9999)
    with pytest.raises(ValueError, match="errors.appointment.not_found"):
        AppointmentService().unmark_no_show(9999)
