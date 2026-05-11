"""Centralized UI appearance (colors, typography, Qt stylesheets). Independent from i18n."""

from ui.theme.palette import StyleReadability
from ui.theme.theme_manager import ThemeManager, apply_application_theme, get_theme

__all__ = ["StyleReadability", "ThemeManager", "apply_application_theme", "get_theme"]
