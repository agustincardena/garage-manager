from __future__ import annotations

from PySide6.QtCore import QPoint, QDate, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.language_service import LanguageService


START_HOUR = 7
END_HOUR = 21
SNAP_MINUTES = 30


def _hhmm_to_minutes(t: str) -> int:
    p = (t or "00:00").strip().split(":")
    h = int(p[0])
    m = int(p[1]) if len(p) > 1 else 0
    return h * 60 + m


def _minutes_to_hhmm(total: int) -> str:
    total = max(0, total) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


def _snap_minutes(m: int) -> int:
    return (m // SNAP_MINUTES) * SNAP_MINUTES


class _AppointmentBlock(QFrame):
    moved = Signal(int, str)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(
        self,
        appt_id: int,
        label: str,
        sub: str,
        top: int,
        height: int,
        parent: QWidget,
        language_service: LanguageService | None = None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self._appt_id = appt_id
        self._drag_start: QPoint | None = None
        self._origin_top = top
        self._dragging = False

        self.setObjectName("apptBlock")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        t = QLabel(label)
        t.setObjectName("scheduleBlockTitle")
        t.setWordWrap(True)
        s = QLabel(sub)
        s.setObjectName("scheduleBlockSub")
        s.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(s)
        t.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        s.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setGeometry(4, top, max(parent.width() - 8, 40), max(height, 24))

    def resize_for_parent(self) -> None:
        pw = self.parentWidget()
        if pw:
            self.setFixedWidth(max(pw.width() - 8, 40))

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.edit_requested.emit(self._appt_id)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self._origin_top = self.y()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        delta = event.globalPosition().toPoint() - self._drag_start
        if not self._dragging and abs(delta.y()) < 6:
            super().mouseMoveEvent(event)
            return
        self._dragging = True
        parent = self.parentWidget()
        if not parent:
            return
        ny = self._origin_top + delta.y()
        ny = max(0, min(parent.height() - self.height(), ny))
        self.move(self.x(), ny)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            parent = self.parentWidget()
            if isinstance(parent, _DayGrid):
                cy = self.y() + self.height() // 2
                new_time = parent.block_top_to_time(cy)
                self.moved.emit(self._appt_id, new_time)
            self._dragging = False
            self._drag_start = None
        else:
            self._drag_start = None
        super().mouseReleaseEvent(event)

    def _menu(self, pos) -> None:
        m = QMenu(self)
        if self._lang is not None:
            m.addAction(
                self._lang.tr("schedule.menu_edit"),
                lambda: self.edit_requested.emit(self._appt_id),
            )
            m.addAction(
                self._lang.tr("schedule.menu_delete"),
                lambda: self.delete_requested.emit(self._appt_id),
            )
        else:
            m.addAction("Edit appointment", lambda: self.edit_requested.emit(self._appt_id))
            m.addAction("Delete appointment", lambda: self.delete_requested.emit(self._appt_id))
        m.exec(self.mapToGlobal(pos))


class _DayGrid(QWidget):
    empty_slot_clicked = Signal(QDate, str)
    appointment_moved = Signal(int, str)
    appointment_edit = Signal(int)
    appointment_delete = Signal(int)

    _SLOT_PX = 26

    @classmethod
    def slot_px(cls) -> int:
        return cls._SLOT_PX

    def __init__(
        self,
        day: QDate,
        parent=None,
        *,
        language_service: LanguageService | None = None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self._day = day
        self._appts: list[dict] = []
        self._blocks: list[_AppointmentBlock] = []
        self._slot_px = self._SLOT_PX
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._recompute_height()

    def day(self) -> QDate:
        return self._day

    def set_day(self, day: QDate) -> None:
        self._day = day
        self._clear_blocks()
        self.update()

    def _recompute_height(self) -> None:
        slots = (END_HOUR - START_HOUR) * (60 // SNAP_MINUTES)
        self.setFixedHeight(slots * self._slot_px + 1)

    def set_appointments(self, rows: list[dict]) -> None:
        self._appts = list(rows)
        self._layout_blocks()

    def _clear_blocks(self) -> None:
        for b in self._blocks:
            b.deleteLater()
        self._blocks.clear()

    def _layout_blocks(self) -> None:
        self._clear_blocks()
        total_min = (END_HOUR - START_HOUR) * 60
        h = self.height()
        if h <= 0:
            return
        for row in self._appts:
            appt_id = int(row["id"])
            start = _hhmm_to_minutes(str(row["appointment_time"]))
            base = START_HOUR * 60
            rel_start = start - base
            if rel_start < 0 or rel_start >= total_min:
                continue
            top = int(rel_start / total_min * h)
            bh = max(int(SNAP_MINUTES / total_min * h), 22)
            plate = (row.get("plate") or "—").upper()
            client = row.get("client_name") or "—"
            vm = f"{row.get('brand') or ''} {row.get('model') or ''}".strip() or "—"
            reason = (row.get("reason") or "").strip()
            sub = f"{plate} · {vm}"
            if reason:
                sub += f"\n{reason}"
            blk = _AppointmentBlock(appt_id, client, sub, top, bh, self, self._lang)
            blk.moved.connect(self.appointment_moved.emit)
            blk.edit_requested.connect(self.appointment_edit.emit)
            blk.delete_requested.connect(self.appointment_delete.emit)
            self._blocks.append(blk)
        for b in self._blocks:
            b.resize_for_parent()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._layout_blocks()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total_slots = (END_HOUR - START_HOUR) * (60 // SNAP_MINUTES)
        w = self.width()
        pen = QPen(QColor("#e2e8f0"))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(total_slots + 1):
            y = i * self._slot_px
            painter.drawLine(0, y, w, y)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            t = self._y_to_time(event.position().y())
            self.empty_slot_clicked.emit(self._day, t)
        super().mousePressEvent(event)

    def _y_to_time(self, y: float) -> str:
        h = self.height()
        if h <= 0:
            return _minutes_to_hhmm(START_HOUR * 60)
        total_min = (END_HOUR - START_HOUR) * 60
        ratio = max(0.0, min(1.0, y / h))
        minutes = START_HOUR * 60 + ratio * total_min
        snapped = _snap_minutes(int(minutes))
        snapped = min(snapped, END_HOUR * 60 - SNAP_MINUTES)
        return _minutes_to_hhmm(snapped)

    def block_top_to_time(self, y_center: int) -> str:
        return self._y_to_time(float(y_center))


class ScheduleCalendarWidget(QWidget):
    empty_slot_clicked = Signal(QDate, str)
    appointment_edit = Signal(int)
    appointment_delete = Signal(int)
    appointment_moved = Signal(int, QDate, str)

    def __init__(
        self,
        parent=None,
        *,
        language_service: LanguageService | None = None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self._mode = "week"
        self._anchor = QDate.currentDate()
        self._rows: list[dict] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._ruler = QWidget()
        self._ruler.setFixedWidth(48)
        rlay = QVBoxLayout(self._ruler)
        rlay.setContentsMargins(0, 28, 0, 0)
        rlay.setSpacing(0)
        slot_px = _DayGrid.slot_px()
        slots = (END_HOUR - START_HOUR) * (60 // SNAP_MINUTES)
        for i in range(slots):
            minute_of_day = START_HOUR * 60 + i * SNAP_MINUTES
            if (i * SNAP_MINUTES) % 60 == 0:
                hour = minute_of_day // 60
                lab = QLabel(f"{hour:02d}:00")
                lab.setObjectName("scheduleRulerHour")
                lab.setFixedHeight(slot_px)
                lab.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
                rlay.addWidget(lab)
            else:
                sp = QWidget()
                sp.setFixedHeight(slot_px)
                rlay.addWidget(sp)
        root.addWidget(self._ruler)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._days_host = QWidget()
        self._days_layout = QHBoxLayout(self._days_host)
        self._days_layout.setContentsMargins(0, 0, 0, 0)
        self._days_layout.setSpacing(8)
        self._scroll.setWidget(self._days_host)
        root.addWidget(self._scroll, stretch=1)

        self._day_widgets: list[tuple[QLabel, _DayGrid]] = []
        self._rebuild_columns()

    def set_mode(self, mode: str) -> None:
        mode = "day" if mode == "day" else "week"
        if mode == self._mode:
            return
        self._mode = mode
        self._rebuild_columns()
        self.set_appointments(self._rows)

    def mode(self) -> str:
        return self._mode

    def set_anchor_date(self, d: QDate) -> None:
        self._anchor = d
        self._rebuild_columns()
        self.set_appointments(self._rows)

    def anchor_date(self) -> QDate:
        return self._anchor

    def visible_date_range(self) -> tuple[QDate, QDate]:
        if self._mode == "day":
            return self._anchor, self._anchor
        mon = self._anchor.addDays(-(self._anchor.dayOfWeek() - 1))
        sun = mon.addDays(6)
        return mon, sun

    def set_appointments(self, rows: list[dict]) -> None:
        self._rows = list(rows)
        start, end = self.visible_date_range()
        d = start
        i = 0
        while d <= end and i < len(self._day_widgets):
            _, grid = self._day_widgets[i]
            day_rows = [
                r
                for r in self._rows
                if str(r.get("appointment_date", "")) == d.toString(Qt.DateFormat.ISODate)
            ]
            grid.set_appointments(day_rows)
            d = d.addDays(1)
            i += 1

    def _rebuild_columns(self) -> None:
        for _, grid in self._day_widgets:
            grid.deleteLater()
        self._day_widgets.clear()
        while self._days_layout.count():
            item = self._days_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        start, end = self.visible_date_range()
        d = start
        while d <= end:
            col = QVBoxLayout()
            col.setSpacing(4)
            col.setContentsMargins(0, 0, 0, 0)
            title = QLabel(
                f"{d.toString('ddd d')}\n{d.toString('MMM yyyy')}"
            )
            title.setObjectName("scheduleDayHeader")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid = _DayGrid(d, language_service=self._lang)
            grid.empty_slot_clicked.connect(self.empty_slot_clicked.emit)
            grid.appointment_moved.connect(self._on_moved)
            grid.appointment_edit.connect(self.appointment_edit.emit)
            grid.appointment_delete.connect(self.appointment_delete.emit)
            col_w = QWidget()
            cl = QVBoxLayout(col_w)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.addWidget(title)
            cl.addWidget(grid)
            self._days_layout.addWidget(col_w, stretch=1)
            self._day_widgets.append((title, grid))
            d = d.addDays(1)

    def _on_moved(self, appt_id: int, new_time: str) -> None:
        grid = self.sender()
        if isinstance(grid, _DayGrid):
            self.appointment_moved.emit(appt_id, grid.day(), new_time)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._mode == "week":
            self._days_host.setMinimumWidth(max(self.width() - 48, 7 * 140))
