"""Spin box that ignores the mouse wheel unless it has focus (V12).

In the sidebar, scrolling the mouse over "Cars per time slot" changed the
setting by accident. The value still changes with the arrows, the keyboard,
or the wheel after clicking the field.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSpinBox


class NoWheelSpinBox(QSpinBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
