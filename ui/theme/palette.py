"""Corporate color tokens (logic-free; appearance only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorporateColors:
    """Primary UI palette (dark theme) — edit here or override via corporate_tokens.json.

    Two background levels only: ``app_bg`` (window) and the card level
    (``surface_page`` / ``surface_muted``, same value as the sidebar and group boxes).
    """

    # Brand / actions
    primary: str = "#2563eb"
    primary_hover: str = "#1d4ed8"
    primary_pressed: str = "#1e40af"
    success: str = "#047857"
    success_hover: str = "#065f46"
    # Money going out (Reports: "Register expense" button and expense bar, V11)
    expense: str = "#c2410c"
    expense_hover: str = "#9a3412"
    danger: str = "#dc2626"
    danger_hover: str = "#b91c1c"
    # Destructive label on a control background (outline danger buttons)
    danger_text: str = "#fca5a5"

    # Surfaces
    app_bg: str = "#0f172a"
    surface_page: str = "#1e293b"
    surface_muted: str = "#1e293b"
    surface_alternate: str = "#243247"
    surface_selected: str = "#1e3a5f"
    border_subtle: str = "#334155"
    border_strong: str = "#475569"

    # Sidebar (same level as cards)
    sidebar_bg: str = "#1e293b"
    sidebar_text: str = "#cbd5e1"
    sidebar_text_hover: str = "#f8fafc"
    sidebar_brand: str = "#f1f5f9"
    sidebar_hover_bg: str = "#334155"

    # Text (all readable on app_bg and on the card level)
    text_primary: str = "#f1f5f9"
    agenda_date_heading: str = "#f1f5f9"
    text_secondary: str = "#cbd5e1"
    text_muted: str = "#94a3b8"
    text_on_primary: str = "#ffffff"
    text_disabled: str = "#94a3b8"

    # Accent fills
    accent_soft: str = "#1e3a8a"
    accent_border: str = "#3b82f6"
    time_emphasis: str = "#93c5fd"

    # Status / feedback
    profit_positive: str = "#4ade80"
    profit_negative: str = "#f87171"
    warning_banner: str = "#fbbf24"

    # Controls (inputs and secondary buttons)
    control_bg: str = "#334155"
    control_hover_bg: str = "#475569"
    control_border: str = "#475569"
    control_disabled_bg: str = "#1e293b"
    scrollbar_handle: str = "#475569"
    scrollbar_handle_hover: str = "#64748b"

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
    # Clickable sizes for a workshop PC (px)
    button_content_height: int = 20
    button_pad_v: int = 8
    button_pad_h: int = 14
    table_row_height: int = 38
    scrollbar_width: int = 12


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
    base_pt: int = 15
    nav_pt: int = 15
    brand_pt: int = 18
    card_time_pt: int = 17
    card_body_pt: int = 15
    card_meta_pt: int = 13
    date_title_pt: int = 20
    ticket_plate_pt: int = 20
    ticket_sub_pt: int = 14
    ticket_problem_pt: int = 15
    detail_plate_pt: int = 26
    detail_value_pt: int = 16
    metric_caption_pt: int = 14
    metric_value_pt: int = 24
    primary_action_pt: int = 16
    schedule_block_title_pt: int = 12
    schedule_block_sub_pt: int = 12
    schedule_ruler_pt: int = 12
    schedule_day_header_pt: int = 15
