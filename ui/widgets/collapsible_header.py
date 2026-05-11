from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class CollapsibleHeaderBar(QFrame):
    """Full-width clickable bar: title (+ optional subtitle) and chevron (▶ / ▼)."""

    clicked = Signal()

    def __init__(self, *, chevron_side: str = "left", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("collapsibleSectionHeader")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._side = "right" if chevron_side == "right" else "left"
        self._expanded = True

        self._chevron = QLabel()
        self._chevron.setObjectName("collapsibleHeaderChevron")
        self._chevron.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._title = QLabel()
        self._title.setObjectName("collapsibleHeaderTitle")
        self._title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._subtitle = QLabel()
        self._subtitle.setObjectName("collapsibleHeaderSubtitle")
        self._subtitle.setWordWrap(True)
        self._subtitle.setVisible(False)
        self._subtitle.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        title_col.addWidget(self._title)
        title_col.addWidget(self._subtitle)

        title_host = QWidget()
        title_host.setLayout(title_col)
        title_host.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)

        if self._side == "left":
            row.addWidget(self._chevron, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(title_host, stretch=1)
        else:
            row.addWidget(title_host, stretch=1)
            row.addWidget(self._chevron, 0, Qt.AlignmentFlag.AlignVCenter)

        self._chevron.setFixedWidth(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.set_expanded(True)

    def set_title(self, text: str) -> None:
        self._title.setText(text)

    def set_subtitle(self, text: str | None) -> None:
        if text:
            self._subtitle.setText(text)
            self._subtitle.setVisible(True)
        else:
            self._subtitle.clear()
            self._subtitle.setVisible(False)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        # Collapsed ▶ , expanded ▼ (same convention for left- and right-chevron layouts)
        self._chevron.setText("▼" if expanded else "▶")

    def expanded(self) -> bool:
        return self._expanded

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SectionHeaderBar(CollapsibleHeaderBar):
    """Thin booking dialog section header: title left, chevron right (same click/chevron behavior)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(chevron_side="right", parent=parent)
        self.setObjectName("bookingSectionHeader")
        lay = self.layout()
        if lay is not None:
            lay.setContentsMargins(12, 6, 12, 6)


def animate_section_height(
    widget: QWidget,
    expand: bool,
    *,
    duration_ms: int = 180,
    on_finished: object | None = None,
) -> None:
    """Animate maximumHeight for smooth expand/collapse; resets max height when done."""
    old = getattr(widget, "_section_height_anim", None)
    if old is not None:
        old.stop()
        old.deleteLater()

    anim = QPropertyAnimation(widget, b"maximumHeight")
    anim.setDuration(duration_ms)
    anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
    widget._section_height_anim = anim

    if expand:

        def _start_expand() -> None:
            widget.setVisible(True)
            widget.setMaximumHeight(0)
            widget.adjustSize()
            target = max(
                widget.sizeHint().height(),
                widget.minimumSizeHint().height(),
                1,
            )
            anim.setStartValue(0)
            anim.setEndValue(min(target + 48, 2000))

            def _on_expand_finished() -> None:
                widget.setMaximumHeight(16777215)
                if callable(on_finished):
                    on_finished()

            anim.finished.connect(_on_expand_finished)
            anim.start()

        QTimer.singleShot(0, _start_expand)
        return

    h = max(widget.height(), widget.sizeHint().height(), 1)
    anim.setStartValue(h)
    anim.setEndValue(0)

    def _on_collapse_finished() -> None:
        widget.setVisible(False)
        widget.setMaximumHeight(16777215)
        if callable(on_finished):
            on_finished()

    anim.finished.connect(_on_collapse_finished)
    anim.start()
