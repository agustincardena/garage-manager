"""Corporate color tokens (logic-free; appearance only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorporateColors:
    """Primary UI palette — edit here or override via corporate_tokens.json."""

    # Brand / actions
    primary: str = "#2563eb"
    primary_hover: str = "#1d4ed8"
    primary_pressed: str = "#1e40af"
    success: str = "#059669"
    success_hover: str = "#047857"
    danger: str = "#b91c1c"

    # Surfaces
    surface_page: str = "#ffffff"
    surface_muted: str = "#f8fafc"
    surface_selected: str = "#eff6ff"
    border_subtle: str = "#e2e8f0"
    border_strong: str = "#cbd5e1"

    # Sidebar (dark strip)
    sidebar_bg: str = "#1e293b"
    sidebar_text: str = "#cbd5e1"
    sidebar_text_hover: str = "#f8fafc"
    sidebar_brand: str = "#f1f5f9"
    sidebar_hover_bg: str = "#334155"

    # Text
    text_primary: str = "#0f172a"
    # Agenda day heading (readable on light surfaces; override via corporate_tokens.json)
    agenda_date_heading: str = "#155e75"
    text_secondary: str = "#334155"
    text_muted: str = "#64748b"
    text_on_primary: str = "#ffffff"
    text_disabled: str = "#f1f5f9"

    # Accent fills
    accent_soft: str = "#dbeafe"
    accent_border: str = "#3b82f6"
    time_emphasis: str = "#1e40af"

    # Status / feedback
    profit_positive: str = "#15803d"
    profit_negative: str = "#b91c1c"
    warning_banner: str = "#b45309"

    # Controls
    control_bg: str = "#ffffff"
    control_border: str = "#e2e8f0"
    control_disabled_bg: str = "#94a3b8"


@dataclass(frozen=True)
class ThemeRadii:
    sm: int = 5
    md: int = 6
    lg: int = 8
    xl: int = 10


@dataclass(frozen=True)
class ThemeSpacing:
    xs: int = 4
    sm: int = 6
    md: int = 8
    lg: int = 10
    xl: int = 14
    xxl: int = 18
    section: int = 20
    empty_pad: int = 24


@dataclass(frozen=True)
class StyleReadability:
    """Contrast and focus tokens; defaults match style_config.json (overridable via that file)."""

    selection_row_background: str = "#1e293b"
    selection_row_text: str = "#e2e8f0"
    selection_row_border: str = "#334155"
    selection_indicator_unchecked_border: str = "#64748b"
    selection_indicator_checked_fill: str = "#3b82f6"
    selection_indicator_checked_border: str = "#93c5fd"
    groupbox_panel_background: str = "#1e293b"
    groupbox_panel_text: str = "#e2e8f0"
    groupbox_title_color: str = "#f8fafc"
    groupbox_frame_color: str = "#475569"
    focus_ring_color: str = "#38bdf8"
    focus_ring_width_px: int = 2
    sidebar_combo_background: str = "#334155"
    sidebar_combo_text: str = "#f1f5f9"
    sidebar_combo_border: str = "#475569"


@dataclass(frozen=True)
class ThemeTypography:
    font_family: str = "Segoe UI, Roboto, system-ui, sans-serif"
    nav_pt: int = 14
    brand_pt: int = 16
    card_time_pt: int = 15
    card_body_pt: int = 13
    card_meta_pt: int = 12
    date_title_pt: int = 18
    ticket_plate_pt: int = 18
    ticket_sub_pt: int = 12
    ticket_problem_pt: int = 13
    detail_plate_pt: int = 15
    metric_caption_pt: int = 13
    metric_value_pt: int = 20
    schedule_block_title_pt: int = 9
    schedule_block_sub_pt: int = 11
    schedule_ruler_pt: int = 11
    schedule_day_header_pt: int = 12
