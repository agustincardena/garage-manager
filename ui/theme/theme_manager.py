"""Builds Qt stylesheets from corporate tokens; keeps appearance separate from i18n and business logic."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

from typing import TYPE_CHECKING

from ui.theme.palette import (
    CorporateColors,
    StyleReadability,
    ThemeRadii,
    ThemeSpacing,
    ThemeTypography,
)

if TYPE_CHECKING:  # Qt is imported lazily so the stylesheet can be built and tested without it.
    from PySide6.QtWidgets import QApplication


def _load_color_overrides() -> dict[str, str]:
    path = Path(__file__).resolve().parent / "corporate_tokens.json"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    valid = {f.name for f in fields(CorporateColors)}
    out: dict[str, str] = {}
    for k, v in data.items():
        if k in valid and isinstance(v, str):
            out[k] = v
    return out


def _merge_colors() -> CorporateColors:
    base = asdict(CorporateColors())
    base.update(_load_color_overrides())
    return CorporateColors(**base)


def _load_style_readability_overrides() -> dict:
    path = Path(__file__).resolve().parent / "style_config.json"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _merge_readability() -> StyleReadability:
    overrides = _load_style_readability_overrides()
    defaults = StyleReadability()
    kwargs = {}
    for f in fields(StyleReadability):
        default_val = getattr(defaults, f.name)
        if f.name in overrides:
            raw = overrides[f.name]
            if isinstance(default_val, int):
                kwargs[f.name] = int(raw)
            else:
                kwargs[f.name] = str(raw)
        else:
            kwargs[f.name] = default_val
    return StyleReadability(**kwargs)


class ThemeManager:
    """Single entry point for corporate look: colors, radii, typography, and generated QSS."""

    def __init__(self) -> None:
        self.colors = _merge_colors()
        self.readability = _merge_readability()
        self.radii = ThemeRadii()
        self.spacing = ThemeSpacing()
        self.typography = ThemeTypography()

    def global_stylesheet(self) -> str:
        c = self.colors
        s = self.readability
        r = self.radii
        t = self.typography
        sp = self.spacing
        fw = s.focus_ring_width_px

        ff = t.font_family

        return f"""
            QWidget {{
                font-family: {ff};
                font-size: {t.base_pt}px;
            }}
            QToolTip {{
                background-color: {c.control_bg};
                color: {c.text_primary};
                border: 1px solid {c.control_border};
                padding: {sp.xs}px {sp.sm}px;
            }}

            /* ----- Shell / navigation ----- */
            QFrame#sidebar {{
                background-color: {c.sidebar_bg};
                border: none;
            }}
            QLabel#sidebarBrand {{
                color: {c.sidebar_brand};
                font-size: {t.brand_pt}px;
                font-weight: 600;
            }}
            QPushButton#navButton {{
                text-align: left;
                padding: {sp.lg}px {sp.xl}px;
                border: {fw}px solid transparent;
                border-radius: {r.md}px;
                color: {c.sidebar_text};
                background: transparent;
                font-size: {t.nav_pt}px;
                font-weight: 500;
            }}
            QPushButton#navButton:hover {{
                background-color: {c.sidebar_hover_bg};
                color: {c.sidebar_text_hover};
            }}
            QPushButton#navButton:checked {{
                background-color: {c.primary};
                color: {c.text_on_primary};
                font-weight: 600;
            }}
            QPushButton#navButton:focus {{
                border-color: {s.focus_ring_color};
            }}

            QFrame#sidebar QComboBox {{
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                padding: {sp.sm}px {sp.md}px;
                min-height: 22px;
            }}
            QFrame#sidebar QComboBox:hover {{
                background-color: {s.groupbox_frame_color};
                border: 1px solid {s.selection_indicator_unchecked_border};
                color: {c.sidebar_text_hover};
            }}
            QFrame#sidebar QComboBox:focus {{
                border: {fw}px solid {c.primary};
            }}
            QFrame#sidebar QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QFrame#sidebar QLabel {{
                color: {c.sidebar_brand};
            }}

            /* ----- Forms (shared) — same palette as sidebar language QComboBox ----- */
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit {{
                padding: {sp.sm}px {sp.md}px;
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                min-height: 22px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus,
            QTimeEdit:focus {{
                border: {fw}px solid {c.primary};
            }}
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled,
            QTimeEdit:disabled {{
                background-color: {s.groupbox_frame_color};
                color: {c.sidebar_text};
                border: 1px solid {s.selection_row_border};
            }}
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover, QTimeEdit:hover {{
                background-color: {s.groupbox_frame_color};
                border: 1px solid {s.selection_indicator_unchecked_border};
                color: {c.sidebar_text_hover};
            }}
            QListWidget {{
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                padding: {sp.xs}px;
            }}
            QListWidget:focus {{
                border: {fw}px solid {c.primary};
            }}
            QListWidget::item:selected {{
                background-color: {c.primary};
                color: {c.text_on_primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
                border: 1px solid {s.sidebar_combo_border};
            }}
            QTextEdit {{
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                padding: {sp.sm}px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QTextEdit:focus {{
                border: {fw}px solid {c.primary};
            }}

            QGroupBox {{
                font-weight: 600;
                color: {s.groupbox_panel_text};
                background-color: {s.groupbox_panel_background};
                border: 1px solid {s.groupbox_frame_color};
                border-radius: {r.lg}px;
                margin-top: {sp.md}px;
                padding-top: {sp.lg}px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {sp.md}px;
                padding: 2px {sp.sm}px;
                color: {s.groupbox_title_color};
                background-color: transparent;
            }}
            QGroupBox QLabel {{
                color: {s.groupbox_panel_text};
            }}

            QRadioButton, QCheckBox {{
                color: {s.selection_row_text};
                spacing: 8px;
                background-color: {s.selection_row_background};
                border: 1px solid {s.selection_row_border};
                border-radius: {r.md}px;
                padding: {sp.sm}px {sp.md}px;
            }}
            QRadioButton:focus, QCheckBox:focus {{
                border: {fw}px solid {s.focus_ring_color};
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
            }}
            QRadioButton::indicator:unchecked {{
                background-color: {s.sidebar_combo_background};
                border: 2px solid {s.selection_indicator_unchecked_border};
                border-radius: 9px;
            }}
            QRadioButton::indicator:checked {{
                background-color: {s.selection_indicator_checked_fill};
                border: 2px solid {s.selection_indicator_checked_border};
                border-radius: 9px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {r.sm}px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {s.sidebar_combo_background};
                border: 2px solid {s.selection_indicator_unchecked_border};
            }}
            QCheckBox::indicator:checked {{
                background-color: {s.selection_indicator_checked_fill};
                border: 2px solid {s.selection_indicator_checked_border};
            }}

            /* ----- Buttons: secondary (default), primary, danger ----- */
            QPushButton {{
                background-color: {c.control_bg};
                color: {c.text_primary};
                border: {fw}px solid {c.control_border};
                border-radius: {r.md}px;
                padding: {sp.button_pad_v}px {sp.button_pad_h}px;
                min-height: {sp.button_content_height}px;
                font-weight: 600;
            }}
            QPushButton:hover:enabled {{
                background-color: {c.control_hover_bg};
            }}
            QPushButton[variant="primary"] {{
                background-color: {c.primary};
                border-color: {c.primary};
                color: {c.text_on_primary};
            }}
            QPushButton[variant="primary"]:hover:enabled {{
                background-color: {c.primary_hover};
                border-color: {c.primary_hover};
            }}
            QPushButton[variant="primary"]:pressed {{
                background-color: {c.primary_pressed};
                border-color: {c.primary_pressed};
            }}
            QPushButton[variant="danger"] {{
                border-color: {c.danger};
                color: {c.danger_text};
            }}
            QPushButton[variant="danger"]:hover:enabled {{
                background-color: {c.danger};
                color: {c.text_on_primary};
            }}
            QPushButton[variant="danger"]:pressed {{
                background-color: {c.danger_hover};
                border-color: {c.danger_hover};
                color: {c.text_on_primary};
            }}
            QPushButton:disabled {{
                background-color: {c.control_disabled_bg};
                border-color: {c.border_subtle};
                color: {c.text_disabled};
            }}
            QPushButton:focus {{
                border-color: {s.focus_ring_color};
            }}

            /* ----- Tables ----- */
            QTableView {{
                background-color: {c.surface_page};
                alternate-background-color: {c.surface_alternate};
                color: {c.text_primary};
                gridline-color: {c.border_subtle};
                border: 1px solid {c.border_subtle};
                border-radius: {r.sm}px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QTableView::item:selected:!active {{
                background-color: {c.accent_soft};
                color: {c.text_primary};
            }}
            QHeaderView::section {{
                background-color: {c.control_bg};
                color: {c.text_primary};
                font-weight: 600;
                padding: {sp.sm}px {sp.md}px;
                border: none;
                border-right: 1px solid {c.border_strong};
                border-bottom: 1px solid {c.border_strong};
            }}
            QTableCornerButton::section {{
                background-color: {c.control_bg};
                border: none;
            }}

            /* ----- Tabs ----- */
            QTabWidget::pane {{
                border: 1px solid {c.border_subtle};
                border-radius: {r.sm}px;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {c.text_secondary};
                font-weight: 600;
                padding: {sp.lg}px {sp.section}px;
                border: none;
                border-bottom: 3px solid transparent;
            }}
            QTabBar::tab:hover {{
                color: {c.text_primary};
                background-color: {c.sidebar_hover_bg};
            }}
            QTabBar::tab:selected {{
                color: {c.text_primary};
                border-bottom: 3px solid {c.primary};
            }}

            /* ----- Scrollbars ----- */
            QScrollBar:vertical {{
                background: transparent;
                width: {sp.scrollbar_width}px;
                margin: 0;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: {sp.scrollbar_width}px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c.scrollbar_handle};
                border-radius: {r.sm}px;
                min-height: 32px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {c.scrollbar_handle};
                border-radius: {r.sm}px;
                min-width: 32px;
            }}
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
                background-color: {c.scrollbar_handle_hover};
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0;
                height: 0;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: none;
            }}

            /* ----- Agenda ----- */
            QLabel#agendaDateTitle {{
                font-size: {t.date_title_pt}px;
                font-weight: 600;
                color: {c.agenda_date_heading};
                background-color: transparent;
            }}
            QLabel#agendaCardTime {{
                font-weight: 700;
                font-size: {t.card_time_pt}px;
                color: {c.time_emphasis};
            }}
            QLabel#agendaCardSub {{
                font-size: {t.card_body_pt}px;
                color: {c.text_primary};
            }}
            QLabel#agendaCardVehicle {{
                font-size: {t.card_meta_pt}px;
                color: {c.text_muted};
            }}
            QLabel#agendaCardReason {{
                font-size: {t.card_meta_pt}px;
                color: {c.text_secondary};
                font-style: italic;
            }}
            QFrame#agendaDayCard {{
                background-color: {c.surface_muted};
                border: 1px solid {c.border_subtle};
                border-radius: {r.lg}px;
            }}
            QFrame#agendaDayCard[selected="true"] {{
                background-color: {c.surface_selected};
                border: 2px solid {c.primary};
            }}
            QLabel#agendaCardWorkshopBadge {{
                color: {c.time_emphasis};
                font-weight: 600;
            }}
            /* Colors come from variant="primary"; this only makes the main action larger. */
            QPushButton#agendaWorkshopBtn {{
                font-size: {t.primary_action_pt}px;
                padding: {sp.lg}px {sp.xxl}px;
                border-radius: {r.lg}px;
            }}
            QLabel#agendaIntro, QLabel#agendaEntryHint {{
                color: {c.text_secondary};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {c.surface_page};
                border-bottom: 1px solid {c.border_subtle};
                padding: {sp.xs}px;
            }}
            QCalendarWidget QToolButton {{
                background: transparent;
                color: {c.text_primary};
                font-size: {t.primary_action_pt}px;
                font-weight: 600;
                border: none;
                border-radius: {r.sm}px;
                padding: {sp.sm}px {sp.md}px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {c.control_hover_bg};
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
                width: 0;
            }}
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {{
                font-size: 22px;
                min-width: 36px;
            }}
            QCalendarWidget QMenu {{
                background-color: {c.control_bg};
                color: {c.text_primary};
            }}
            QCalendarWidget QMenu::item:selected {{
                background-color: {c.primary};
                color: {c.text_on_primary};
            }}
            QCalendarWidget QAbstractItemView {{
                background-color: {c.surface_page};
                color: {c.text_primary};
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
                outline: 0;
                border: none;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {c.text_disabled};
            }}
            QFrame#agendaContactShell {{
                background-color: transparent;
                border: none;
            }}
            QFrame#collapsibleSectionHeader {{
                background-color: {s.sidebar_combo_background};
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.md}px;
            }}
            QFrame#collapsibleSectionHeader:hover {{
                background-color: {c.sidebar_hover_bg};
                border: 1px solid {s.selection_indicator_unchecked_border};
            }}
            QLabel#collapsibleHeaderChevron {{
                color: #f8fafc;
                font-size: 11px;
                font-weight: 700;
            }}
            QLabel#collapsibleHeaderTitle {{
                color: {c.sidebar_text_hover};
                font-size: {t.schedule_day_header_pt}px;
                font-weight: 600;
            }}
            QLabel#collapsibleHeaderSubtitle {{
                color: {c.text_muted};
                font-size: {t.card_meta_pt}px;
            }}
            QFrame#bookingCollapsibleCard {{
                background-color: transparent;
                border: none;
            }}
            QListWidget#agendaContactList {{
                border: none;
                background-color: transparent;
                color: {s.sidebar_combo_text};
                padding: {sp.xs}px;
            }}
            QListWidget#agendaContactList::item {{
                padding: {sp.xs}px {sp.sm}px;
                border-radius: {r.sm}px;
            }}
            QListWidget#agendaContactList::item:selected {{
                background-color: {c.primary};
                color: {c.text_on_primary};
            }}
            QListWidget#bookingDialogClientList {{
                border: none;
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                padding: {sp.xs}px;
            }}
            QListWidget#bookingDialogClientList::item {{
                padding: {sp.xs}px {sp.sm}px;
                border-radius: {r.sm}px;
            }}
            QListWidget#bookingDialogClientList::item:selected {{
                background-color: {c.primary};
                color: {c.text_on_primary};
            }}

            QFrame#bookingSectionHeader {{
                background-color: {s.sidebar_combo_background};
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                min-height: 34px;
            }}
            QFrame#bookingSectionHeader:hover {{
                background-color: {c.sidebar_hover_bg};
                border: 1px solid {s.selection_indicator_unchecked_border};
            }}

            QFrame#bookingFormSection {{
                background-color: transparent;
                border: none;
            }}
            QLabel#bookingSectionLabel {{
                color: {c.text_secondary};
                font-size: {t.card_meta_pt}px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                padding: 0 0 4px 0;
            }}

            QFrame#bookingDialogFooter {{
                background-color: {c.surface_page};
                border-top: 1px solid {c.border_subtle};
            }}
            QPushButton#bookingDialogSaveBtn {{
                min-width: 100px;
            }}
            QPushButton#bookingDialogCancelBtn {{
                min-width: 88px;
            }}
            QPushButton#bookingGhostLink {{
                background: transparent;
                border: none;
                color: {c.time_emphasis};
                font-weight: 500;
                min-height: 0;
                text-align: left;
                padding: 2px 0;
            }}
            QPushButton#bookingGhostLink:hover:enabled {{
                background: transparent;
                color: {c.text_primary};
            }}

            /* ----- Workshop ----- */
            QFrame#ticketCard {{
                background-color: {c.surface_page};
                border: 1px solid {c.border_subtle};
                border-radius: {r.xl}px;
            }}
            QFrame#ticketCard[ticketSelected="true"] {{
                border: 2px solid {c.accent_border};
                background-color: {c.surface_selected};
            }}
            QLabel#ticketPlate {{
                font-size: {t.ticket_plate_pt}px;
                font-weight: 700;
                color: {c.text_primary};
            }}
            QLabel#ticketSub {{
                font-size: {t.ticket_sub_pt}px;
                color: {c.text_muted};
            }}
            QLabel#ticketProblem {{
                font-size: {t.ticket_problem_pt}px;
                color: {c.text_secondary};
            }}
            QLabel#detailPlate {{
                font-size: {t.detail_plate_pt}px;
                font-weight: 700;
                color: {c.text_primary};
            }}
            QLabel#detailCaption {{
                font-size: {t.card_meta_pt}px;
                font-weight: 400;
                color: {c.text_muted};
                padding-top: {sp.sm}px;
            }}
            QLabel#detailValue {{
                font-size: {t.detail_value_pt}px;
                color: {c.text_primary};
            }}

            /* ----- Reports ----- */
            QLabel#reportsMetricCaption {{
                color: {c.text_muted};
                font-size: {t.metric_caption_pt}px;
            }}
            QLabel#reportsMatplotlibHint {{
                color: {c.warning_banner};
                padding: {sp.md}px;
            }}
            QLabel#reportsLedgerNote {{
                color: {c.text_muted};
                font-size: {t.card_meta_pt}px;
            }}
            /* Income uses variant="primary". Expense keeps its own color until V11. */
            QPushButton#reportsRegisterExpenseBtn {{
                background-color: {c.success};
                border-color: {c.success};
                color: {c.text_on_primary};
            }}
            QPushButton#reportsRegisterExpenseBtn:hover:enabled {{
                background-color: {c.success_hover};
                border-color: {c.success_hover};
            }}

            /* ----- Schedule widget ----- */
            QFrame#apptBlock {{
                background-color: {c.accent_soft};
                border: 1px solid {c.accent_border};
                border-radius: {r.sm}px;
            }}
            QLabel#scheduleBlockTitle {{
                color: {c.text_primary};
                font-size: {t.schedule_block_title_pt}px;
                font-weight: 700;
            }}
            QLabel#scheduleBlockSub {{
                color: {c.text_secondary};
                font-size: {t.schedule_block_sub_pt}px;
            }}
            QLabel#scheduleRulerHour {{
                color: {c.text_muted};
                font-size: {t.schedule_ruler_pt}px;
            }}
            QLabel#scheduleDayHeader {{
                font-weight: 600;
                color: {c.text_primary};
                font-size: {t.schedule_day_header_pt}px;
                padding: {sp.xs}px;
            }}

            /* ----- Empty / muted states ----- */
            QLabel#emptyStateMuted {{
                color: {c.text_muted};
                padding: {sp.empty_pad}px;
            }}
        """

    def calendar_text_colors(self) -> dict[str, str]:
        """Foreground/background for the month calendar's text formats (V2).

        Kept Qt-free so the contrast can be tested; the Agenda turns them into
        QTextCharFormat objects.
        """
        c = self.colors
        return {
            "background": c.surface_page,
            "weekday": c.text_primary,
            "weekend": c.danger_text,
            "header": c.text_secondary,
            "today_text": c.text_on_primary,
            "today_background": c.accent_soft,
        }

    def stylesheet_profit_metric(self, state: str) -> str:
        """Inline style for the profit amount label (dynamic sign)."""
        c = self.colors
        t = self.typography
        if state == "positive":
            color = c.profit_positive
        elif state == "negative":
            color = c.profit_negative
        else:
            color = c.text_primary
        return f"color: {color}; font-size: {t.metric_value_pt}px; font-weight: bold;"


_theme: ThemeManager | None = None


def get_theme() -> ThemeManager:
    global _theme
    if _theme is None:
        _theme = ThemeManager()
    return _theme


def application_palette_roles(colors: CorporateColors) -> dict[str, str]:
    """QPalette role name -> color for the dark theme (kept Qt-free so it can be tested)."""
    return {
        "Window": colors.app_bg,
        "WindowText": colors.text_primary,
        "Base": colors.surface_page,
        "AlternateBase": colors.surface_alternate,
        "Text": colors.text_primary,
        "Button": colors.control_bg,
        "ButtonText": colors.text_primary,
        "BrightText": colors.text_on_primary,
        "Highlight": colors.primary,
        "HighlightedText": colors.text_on_primary,
        "ToolTipBase": colors.control_bg,
        "ToolTipText": colors.text_primary,
        "PlaceholderText": colors.text_muted,
        "Link": colors.time_emphasis,
    }


def apply_application_theme(app: QApplication) -> None:
    """Apply Fusion + an explicit dark palette + the corporate stylesheet on the QApplication.

    The palette is set explicitly so the app looks the same whether Windows is in
    light or dark mode (Fusion otherwise follows the system color scheme).
    """
    from PySide6.QtGui import QColor, QPalette

    theme = get_theme()
    app.setStyle("Fusion")
    pal = QPalette()
    for role_name, color in application_palette_roles(theme.colors).items():
        pal.setColor(getattr(QPalette.ColorRole, role_name), QColor(color))
    disabled = QColor(theme.colors.text_disabled)
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        pal.setColor(QPalette.ColorGroup.Disabled, role, disabled)
    app.setPalette(pal)
    app.setStyleSheet(theme.global_stylesheet())
