"""Builds Qt stylesheets from corporate tokens; keeps appearance separate from i18n and business logic."""

from __future__ import annotations

import json
from dataclasses import asdict, fields
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from ui.theme.palette import (
    CorporateColors,
    StyleReadability,
    ThemeRadii,
    ThemeSpacing,
    ThemeTypography,
)


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
                border: none;
                border-radius: {r.md}px;
                color: {c.sidebar_text};
                background: transparent;
                font-size: {t.nav_pt}px;
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
                border: {fw}px solid {s.focus_ring_color};
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
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
                padding: {sp.sm}px {sp.md}px;
                border: 1px solid {s.sidebar_combo_border};
                border-radius: {r.sm}px;
                background-color: {s.sidebar_combo_background};
                color: {s.sidebar_combo_text};
                min-height: 22px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                border: {fw}px solid {c.primary};
            }}
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
                background-color: {s.groupbox_frame_color};
                color: {c.sidebar_text};
                border: 1px solid {s.selection_row_border};
            }}
            QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QDateEdit:hover {{
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

            QPushButton:focus {{
                border: {fw}px solid {s.focus_ring_color};
            }}
            QPushButton#agendaWorkshopBtn:focus, QPushButton#reportsRegisterIncomeBtn:focus,
            QPushButton#reportsRegisterExpenseBtn:focus {{
                border: {fw}px solid {s.focus_ring_color};
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
            QPushButton#agendaDeleteBtn {{
                color: {c.danger};
            }}
            QPushButton#agendaWorkshopBtn {{
                background-color: {c.primary};
                color: {c.text_on_primary};
                font-weight: 600;
                font-size: 15px;
                padding: {sp.lg}px {sp.xxl}px;
                border-radius: {r.lg}px;
                border: none;
            }}
            QPushButton#agendaWorkshopBtn:hover:enabled {{
                background-color: {c.primary_hover};
            }}
            QPushButton#agendaWorkshopBtn:disabled {{
                background-color: {c.control_disabled_bg};
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
                color: {c.text_muted};
                font-size: {t.card_meta_pt}px;
                font-weight: 600;
                letter-spacing: 0.04em;
                text-transform: uppercase;
                padding: 0 0 4px 0;
            }}

            QDialog#bookingDialog QLineEdit,
            QDialog#bookingDialog QComboBox,
            QDialog#bookingDialog QDateEdit,
            QDialog#bookingDialog QTextEdit {{
                background-color: #2b2b2b;
                color: #e8e8e8;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                padding: {sp.sm}px {sp.md}px;
                min-height: 22px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QDialog#bookingDialog QLineEdit:focus,
            QDialog#bookingDialog QComboBox:focus,
            QDialog#bookingDialog QDateEdit:focus,
            QDialog#bookingDialog QTextEdit:focus {{
                border: {fw}px solid {c.primary};
            }}
            QDialog#bookingDialog QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QDialog#bookingDialog QComboBox QAbstractItemView {{
                background-color: #2b2b2b;
                color: #e8e8e8;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                selection-background-color: {c.primary};
                selection-color: {c.text_on_primary};
            }}
            QDialog#bookingDialog QListWidget#bookingDialogClientList {{
                background-color: #2b2b2b;
                color: #e8e8e8;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }}

            QFrame#bookingDialogFooter {{
                background-color: {s.sidebar_combo_background};
                border-top: 1px solid #3d3d3d;
            }}
            QPushButton#bookingDialogSaveBtn {{
                background-color: {c.primary};
                color: {c.text_on_primary};
                font-weight: 600;
                padding: 10px 28px;
                border-radius: 8px;
                border: none;
                min-width: 100px;
            }}
            QPushButton#bookingDialogSaveBtn:hover:enabled {{
                background-color: {c.primary_hover};
            }}
            QPushButton#bookingDialogCancelBtn {{
                background-color: #3a3a3a;
                color: #e2e8f0;
                font-weight: 500;
                padding: 10px 22px;
                border-radius: 8px;
                border: 1px solid #4a4a4a;
                min-width: 88px;
            }}
            QPushButton#bookingDialogCancelBtn:hover {{
                background-color: #4a4a4a;
                border: 1px solid #5a5a5a;
            }}
            QPushButton#bookingGhostLink {{
                background: transparent;
                border: none;
                color: {c.primary};
                font-weight: 500;
                text-align: left;
                padding: 2px 0;
            }}
            QPushButton#bookingGhostLink:hover {{
                color: {c.primary_hover};
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
                font-weight: 600;
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
            QPushButton#reportsRegisterIncomeBtn {{
                background-color: {c.primary};
                color: {c.text_on_primary};
                font-weight: 600;
                padding: {sp.lg}px {sp.xxl}px;
                border-radius: {r.lg}px;
                border: none;
            }}
            QPushButton#reportsRegisterIncomeBtn:hover {{
                background-color: {c.primary_hover};
            }}
            QPushButton#reportsRegisterExpenseBtn {{
                background-color: {c.success};
                color: {c.text_on_primary};
                font-weight: 600;
                padding: {sp.lg}px {sp.xxl}px;
                border-radius: {r.lg}px;
                border: none;
            }}
            QPushButton#reportsRegisterExpenseBtn:hover {{
                background-color: {c.success_hover};
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

    def stylesheet_profit_metric(self, state: str) -> str:
        """Inline style for the profit amount label (dynamic sign)."""
        c = self.colors
        t = self.typography
        if state == "positive":
            color = c.profit_positive
        elif state == "negative":
            color = c.profit_negative
        else:
            color = c.text_muted
        return f"color: {color}; font-size: {t.metric_value_pt}px; font-weight: bold;"


_theme: ThemeManager | None = None


def get_theme() -> ThemeManager:
    global _theme
    if _theme is None:
        _theme = ThemeManager()
    return _theme


def apply_application_theme(app: QApplication) -> None:
    """Apply Fusion + corporate stylesheet once on the QApplication (children inherit)."""
    app.setStyle("Fusion")
    app.setStyleSheet(get_theme().global_stylesheet())
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))
    app.setPalette(pal)
