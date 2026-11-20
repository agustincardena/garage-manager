"""Visual theme (V1, V5, V7, V8, V9): tokens and generated stylesheet.

These tests do not need Qt: the stylesheet is plain text built from the tokens.
"""

from __future__ import annotations

import re

import pytest

from ui.theme.contrast import contrast_ratio
from ui.theme.palette import CorporateColors, StyleReadability, ThemeSpacing, ThemeTypography
from ui.theme.theme_manager import ThemeManager, application_palette_roles

AA_NORMAL_TEXT = 4.5

COLORS = CorporateColors()
READABILITY = StyleReadability()


@pytest.fixture(scope="module")
def qss() -> str:
    return ThemeManager().global_stylesheet()


def test_contrast_ratio_reference_values():
    assert contrast_ratio("#ffffff", "#000000") == pytest.approx(21.0)
    assert contrast_ratio("#777777", "#777777") == pytest.approx(1.0)


# --- V7: text contrast -------------------------------------------------------

@pytest.mark.parametrize(
    "text_token",
    ["text_primary", "text_secondary", "text_muted", "agenda_date_heading", "time_emphasis",
     "profit_positive", "profit_negative", "warning_banner"],
)
@pytest.mark.parametrize("background_token", ["app_bg", "surface_page", "surface_muted"])
def test_text_is_readable_on_both_background_levels(text_token, background_token):
    ratio = contrast_ratio(getattr(COLORS, text_token), getattr(COLORS, background_token))
    assert ratio >= AA_NORMAL_TEXT, f"{text_token} on {background_token}: {ratio:.2f}"


@pytest.mark.parametrize(
    "foreground, background",
    [
        (COLORS.text_on_primary, COLORS.primary),
        (COLORS.text_on_primary, COLORS.primary_hover),
        (COLORS.text_on_primary, COLORS.danger),
        (COLORS.text_on_primary, COLORS.success),
        (COLORS.text_primary, COLORS.control_bg),
        (COLORS.text_primary, COLORS.control_hover_bg),
        (COLORS.danger_text, COLORS.control_bg),
        (COLORS.text_disabled, COLORS.control_disabled_bg),
        (COLORS.text_primary, COLORS.surface_selected),
        (COLORS.text_primary, COLORS.accent_soft),
        (COLORS.text_primary, COLORS.surface_alternate),
        (READABILITY.groupbox_panel_text, READABILITY.groupbox_panel_background),
        (READABILITY.sidebar_combo_text, READABILITY.sidebar_combo_background),
    ],
)
def test_control_labels_are_readable(foreground, background):
    assert contrast_ratio(foreground, background) >= AA_NORMAL_TEXT


# --- V8: two background levels -----------------------------------------------

def test_only_two_background_levels():
    card_level = {COLORS.surface_page, COLORS.surface_muted, COLORS.sidebar_bg,
                  READABILITY.groupbox_panel_background}
    assert len(card_level) == 1
    assert COLORS.app_bg not in card_level


def test_palette_is_explicit_and_dark():
    roles = application_palette_roles(COLORS)
    assert roles["Window"] == COLORS.app_bg
    assert roles["Base"] == COLORS.surface_page
    assert roles["Highlight"] == COLORS.primary
    for role in ("Window", "Base", "AlternateBase", "Button"):
        assert contrast_ratio(roles["Text"], roles[role]) >= AA_NORMAL_TEXT


def test_stylesheet_has_no_private_greys(qss):
    """The booking dialog used its own grey palette (#2b2b2b...); everything now uses tokens."""
    for grey in ("#2b2b2b", "#3a3a3a", "#3d3d3d", "#4a4a4a", "#5a5a5a"):
        assert grey not in qss


# --- V1: button tiers --------------------------------------------------------

def test_stylesheet_is_well_formed(qss):
    assert qss.count("{") == qss.count("}")
    assert "None" not in qss
    assert not re.search(r"\{[a-z_]+\.[a-z_]+\}", qss), "unresolved token placeholder"


@pytest.mark.parametrize(
    "selector",
    ['QPushButton {', 'QPushButton[variant="primary"] {', 'QPushButton[variant="danger"] {',
     "QPushButton:disabled {", "QPushButton:focus {"],
)
def test_button_tiers_are_defined(qss, selector):
    assert selector in qss


def test_disabled_rule_comes_after_variants(qss):
    """Same specificity: the later rule wins, so a disabled primary button looks disabled."""
    assert qss.index("QPushButton:disabled {") > qss.index('QPushButton[variant="danger"]:pressed {')


def test_buttons_are_at_least_40px_tall():
    sp = ThemeSpacing()
    border = StyleReadability().focus_ring_width_px
    assert sp.button_content_height + 2 * sp.button_pad_v + 2 * border >= 40


def test_time_edit_shares_the_form_field_style(qss):
    assert "QDateEdit, QTimeEdit {" in qss


# --- V5: sizes ---------------------------------------------------------------

def test_base_font_and_row_height_fit_a_workshop_pc(qss):
    t = ThemeTypography()
    assert t.base_pt >= 15
    assert f"font-size: {t.base_pt}px;" in qss
    assert ThemeSpacing().table_row_height >= 36
    small = {name: value for name, value in vars(t).items()
             if name.endswith("_pt") and value < 12}
    assert not small, f"font sizes below 12px: {small}"


# --- V9: row selection -------------------------------------------------------

def test_table_selection_uses_the_accent_color(qss):
    table_rule = qss[qss.index("QTableView {"):qss.index("QTableView::item:selected:!active")]
    assert f"selection-background-color: {COLORS.primary};" in table_rule
    inactive = qss[qss.index("QTableView::item:selected:!active"):qss.index("QHeaderView::section")]
    assert f"background-color: {COLORS.accent_soft};" in inactive


# --- V2: month calendar ------------------------------------------------------

@pytest.mark.parametrize("key", ["weekday", "weekend", "header"])
def test_calendar_day_numbers_are_readable(key):
    colors = ThemeManager().calendar_text_colors()
    assert contrast_ratio(colors[key], colors["background"]) >= AA_NORMAL_TEXT


def test_calendar_today_is_readable_and_stands_out():
    colors = ThemeManager().calendar_text_colors()
    assert contrast_ratio(colors["today_text"], colors["today_background"]) >= AA_NORMAL_TEXT
    assert colors["today_background"] != colors["background"]


def test_calendar_selected_day_uses_the_primary_color(qss):
    rule = qss[qss.index("QCalendarWidget QAbstractItemView {"):]
    rule = rule[:rule.index("}")]
    assert f"selection-background-color: {COLORS.primary};" in rule


def test_calendar_month_button_has_no_dropdown_mark(qss):
    """The default menu indicator showed as a stray underscore after the month name."""
    assert "QCalendarWidget QToolButton::menu-indicator {" in qss


# --- V11: Reports colors -----------------------------------------------------

def test_expense_button_is_readable_and_not_green():
    assert contrast_ratio(COLORS.text_on_primary, COLORS.expense) >= AA_NORMAL_TEXT
    assert contrast_ratio(COLORS.text_on_primary, COLORS.expense_hover) >= AA_NORMAL_TEXT
    assert COLORS.expense not in (COLORS.success, COLORS.profit_positive)


def test_expense_button_uses_the_expense_color(qss):
    rule = qss[qss.index("QPushButton#reportsRegisterExpenseBtn {"):]
    rule = rule[:rule.index("}")]
    assert f"background-color: {COLORS.expense};" in rule


# --- V10: booking dialog section headers -------------------------------------

def test_booking_section_header_reads_as_a_title(qss):
    rule = qss[qss.index("QFrame#bookingSectionHeader {"):]
    rule = rule[:rule.index("}")]
    assert "background-color: transparent;" in rule
    assert "border: none;" in rule


# --- V12 / V13 ---------------------------------------------------------------

@pytest.mark.parametrize(
    "selector",
    ["QFrame#sidebarSeparator {", "QFrame#sidebar QLabel#sidebarSettingLabel {",
     "QPushButton#workshopRefreshBtn {"],
)
def test_low_weight_elements_are_styled(qss, selector):
    assert selector in qss
