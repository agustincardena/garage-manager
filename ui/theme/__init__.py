"""Centralized UI appearance (colors, typography, Qt stylesheets). Independent from i18n."""

from ui.theme.palette import StyleReadability
from ui.theme.theme_manager import ThemeManager, apply_application_theme, get_theme

BUTTON_PRIMARY = "primary"
BUTTON_DANGER = "danger"


def set_button_variant(button, variant: str) -> None:
    """Mark a QPushButton as primary or danger; unmarked buttons are secondary.

    Must be called before the button is shown (the stylesheet reads the property once).
    """
    button.setProperty("variant", variant)


def apply_table_metrics(table) -> None:
    """Give a QTableView the theme row height (easier to read and click in the workshop)."""
    table.verticalHeader().setDefaultSectionSize(get_theme().spacing.table_row_height)


__all__ = [
    "BUTTON_DANGER",
    "BUTTON_PRIMARY",
    "StyleReadability",
    "ThemeManager",
    "apply_application_theme",
    "apply_table_metrics",
    "get_theme",
    "set_button_variant",
]
