"""UI texts and detail styling for V3 (Agenda entry button) and V4 (workshop detail)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui.theme.palette import CorporateColors, ThemeTypography
from ui.theme.theme_manager import ThemeManager

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"
LANGS = ("es", "en")


def _load(lang: str) -> dict[str, str]:
    return json.loads((LOCALE_DIR / f"{lang}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module", params=LANGS)
def texts(request) -> dict[str, str]:
    return _load(request.param)


def test_both_languages_have_the_same_keys():
    assert set(_load("es")) == set(_load("en"))


# --- V3 ----------------------------------------------------------------------

def test_entry_button_text_is_short(texts):
    assert len(texts["agenda.enter_workshop"]) <= 20


@pytest.mark.parametrize("key", ["agenda.intro", "agenda.entry_hint"])
def test_agenda_help_does_not_rely_on_a_color(texts, key):
    for color_word in ("azul", "blue", "verde", "green"):
        assert color_word not in texts[key].lower()


def test_agenda_hint_names_the_entry_button(texts):
    assert texts["agenda.enter_workshop"] in texts["agenda.entry_hint"]


# --- V2 ----------------------------------------------------------------------

def test_agenda_intro_is_a_single_line(texts):
    assert "\n" not in texts["agenda.intro"]


def test_past_day_empty_state_explains_why_booking_is_disabled(texts):
    assert texts["agenda.empty_past"].startswith(texts["agenda.empty"])
    assert texts["agenda.empty_past"] != texts["agenda.empty"]


# --- V4 ----------------------------------------------------------------------

def test_workshop_has_an_empty_detail_message(texts):
    assert texts["workshop.detail_empty"].strip()


def test_detail_hierarchy_plate_then_values_then_captions():
    t = ThemeTypography()
    assert t.detail_plate_pt > t.detail_value_pt > t.card_meta_pt


def test_detail_captions_are_muted_and_values_are_primary():
    qss = ThemeManager().global_stylesheet()
    c = CorporateColors()
    caption = qss[qss.index("QLabel#detailCaption {"):qss.index("QLabel#detailValue {")]
    value = qss[qss.index("QLabel#detailValue {"):]
    value = value[:value.index("}")]
    assert f"color: {c.text_muted};" in caption
    assert f"color: {c.text_primary};" in value


# --- V6 ----------------------------------------------------------------------

def test_history_parts_column_is_not_abbreviated(texts):
    assert not texts["workshop.history_col_parts"].endswith(".")


def test_history_summary_has_a_hint_when_nothing_is_selected(texts):
    assert texts["workshop.history_summary_empty"].strip()


# --- V11 ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "key", ["reports.income_manual", "reports.income_manual_quarter", "reports.income_manual_year"]
)
def test_income_table_title_does_not_say_manual(texts, key):
    """The table also lists finished orders, so it is not only manual income."""
    assert "manual" not in texts[key].lower()


# --- V12 ---------------------------------------------------------------------

def test_sidebar_language_setting_has_a_label(texts):
    assert texts["settings.language_label"].strip()


# --- V13 ---------------------------------------------------------------------

def test_workshop_empty_state_mentions_both_ways_in(texts):
    empty = texts["workshop.empty_tickets"]
    assert texts["nav.agenda"] in empty
    assert texts["workshop.new_order"] in empty
