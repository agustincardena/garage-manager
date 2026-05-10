from PySide6.QtCore import QDate, QLocale, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.language_service import LanguageService
from services.vehicle_service import VehicleService
from ui.views.booking_dialog import BookingDialog
from ui.widgets.collapsible_header import CollapsibleHeaderBar, animate_section_height


class _DayAppointmentCard(QFrame):
    """One appointment card: click selects; inner buttons do not change selection."""

    card_clicked = Signal(int)

    def __init__(
        self,
        language_service: LanguageService,
        appointment_id: int,
        time_str: str,
        client: str,
        plate: str,
        vehicle: str,
        reason: str,
        parent=None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self.appointment_id = appointment_id
        self.setObjectName("agendaDayCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QHBoxLayout()
        time_l = QLabel(time_str)
        time_l.setObjectName("agendaCardTime")
        top.addWidget(time_l)
        top.addStretch(1)
        btn_edit = QPushButton()
        btn_edit.setFixedWidth(72)
        btn_del = QPushButton()
        btn_del.setFixedWidth(72)
        btn_del.setObjectName("agendaDeleteBtn")
        top.addWidget(btn_edit)
        top.addWidget(btn_del)
        lay.addLayout(top)

        sub = QLabel(f"{client} · {(plate or '—').upper()}")
        sub.setWordWrap(True)
        sub.setObjectName("agendaCardSub")
        lay.addWidget(sub)
        if vehicle.strip():
            vm = QLabel(vehicle.strip())
            vm.setWordWrap(True)
            vm.setObjectName("agendaCardVehicle")
            lay.addWidget(vm)
        if reason.strip():
            r = QLabel(reason.strip())
            r.setWordWrap(True)
            r.setObjectName("agendaCardReason")
            lay.addWidget(r)

        self._btn_edit = btn_edit
        self._btn_del = btn_del
        self._apply_card_translations()

    def _apply_card_translations(self) -> None:
        self._btn_edit.setText(self._lang.tr("agenda.card_edit"))
        self._btn_del.setText(self._lang.tr("agenda.card_delete"))

    def set_selected(self, on: bool) -> None:
        self.setProperty("selected", on)
        self.style().unpolish(self)
        self.style().polish(self)

    def _is_descendant_button(self, pos) -> bool:
        w = self.childAt(pos)
        while w is not None and w is not self:
            if isinstance(w, QPushButton):
                return True
            w = w.parentWidget()
        return False

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_descendant_button(event.pos()):
                self.card_clicked.emit(self.appointment_id)
        super().mousePressEvent(event)


class AgendaView(QWidget):
    def __init__(self, language_service: LanguageService, parent=None):
        super().__init__(parent)
        self._lang = language_service
        self._vehicle_service = VehicleService()
        self._client_service = ClientService()
        self._appointment_service = AppointmentService()

        self._cards: dict[int, _DayAppointmentCard] = {}
        self._selected_appointment_id: int | None = None

        self._intro = QLabel()
        self._intro.setWordWrap(True)
        self._intro.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self._month_cal = QCalendarWidget()
        self._month_cal.setGridVisible(True)
        self._month_cal.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.ISOWeekNumbers
        )
        self._month_cal.setMaximumSize(340, 300)
        self._month_cal.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        today = QDate.currentDate()
        self._month_cal.setSelectedDate(today)
        self._month_cal.selectionChanged.connect(self._on_calendar_day_changed)

        cal_column = QWidget()
        cal_column.setMaximumWidth(380)
        cal_column.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        cal_lay = QVBoxLayout(cal_column)
        cal_lay.setContentsMargins(0, 0, 12, 0)
        cal_lay.addWidget(self._intro)
        cal_wrap = QWidget()
        wrap_l = QHBoxLayout(cal_wrap)
        wrap_l.setContentsMargins(0, 0, 0, 0)
        wrap_l.addStretch(1)
        wrap_l.addWidget(self._month_cal, alignment=Qt.AlignmentFlag.AlignHCenter)
        wrap_l.addStretch(1)
        cal_lay.addWidget(cal_wrap)
        self._contact_section_expanded = False
        self._contact_shell = QFrame()
        self._contact_shell.setObjectName("agendaContactShell")
        self._contact_shell.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        contact_lay = QVBoxLayout(self._contact_shell)
        contact_lay.setContentsMargins(0, 0, 0, 0)
        contact_lay.setSpacing(0)
        self._contact_header = CollapsibleHeaderBar(chevron_side="left")
        self._contact_header.set_expanded(False)
        self._contact_header.clicked.connect(self._on_contact_header_clicked)
        self._contact_search = QLineEdit()
        self._contact_search.textChanged.connect(self._reload_contact_list)
        self._contact_list = QListWidget()
        self._contact_list.setObjectName("agendaContactList")
        self._contact_list.setFrameShape(QFrame.Shape.NoFrame)
        self._contact_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._contact_list.setMinimumHeight(180)
        self._contact_body = QWidget()
        body_lay = QVBoxLayout(self._contact_body)
        body_lay.setContentsMargins(0, 8, 0, 0)
        body_lay.setSpacing(8)
        body_lay.addWidget(self._contact_search)
        body_lay.addWidget(self._contact_list, stretch=1)
        self._contact_body.setVisible(False)
        self._contact_body.setMaximumHeight(0)
        contact_lay.addWidget(self._contact_header)
        contact_lay.addWidget(self._contact_body, stretch=1)
        cal_lay.addWidget(self._contact_shell, stretch=1)
        cal_lay.addStretch(1)

        self._date_title = QLabel()
        self._date_title.setObjectName("agendaDateTitle")
        self._date_title.setTextFormat(Qt.TextFormat.PlainText)
        self._date_title.setWordWrap(True)

        self._btn_add = QPushButton()
        self._btn_add.setMinimumHeight(36)
        self._btn_add.clicked.connect(self._on_add_turn)

        header = QHBoxLayout()
        header.addWidget(self._date_title, stretch=1)
        header.addWidget(self._btn_add)

        self._list_host = QWidget()
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._list_host)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._btn_entry = QPushButton()
        self._btn_entry.setObjectName("agendaWorkshopBtn")
        self._btn_entry.setMinimumHeight(52)
        self._btn_entry.setEnabled(False)
        self._btn_entry.clicked.connect(self._on_workshop_from_turn)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.addLayout(header)
        rl.addWidget(scroll, stretch=1)
        rl.addWidget(self._btn_entry)

        self._split = QSplitter(Qt.Orientation.Horizontal)
        self._split.addWidget(cal_column)
        self._split.addWidget(right)
        self._split.setStretchFactor(0, 0)
        self._split.setStretchFactor(1, 1)
        self._split.setSizes([380, 720])

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._split, stretch=1)

        self.apply_translations()
        self._update_date_title()
        self._update_add_button_enabled()
        self._reload_day_list()
        self._reload_contact_list()

    def apply_translations(self) -> None:
        self._intro.setText(self._lang.tr("agenda.intro"))
        self._btn_add.setText(self._lang.tr("agenda.add_booking"))
        self._btn_entry.setText(self._lang.tr("agenda.enter_workshop"))
        self._contact_header.set_title(self._lang.tr("agenda.contact_info_title"))
        self._contact_header.set_subtitle(None)
        self._contact_search.setPlaceholderText(
            self._lang.tr("agenda.contact_search_placeholder")
        )
        self._contact_header.set_expanded(self._contact_section_expanded)
        self._update_date_title()
        self._update_add_button_enabled()
        self._reload_day_list()
        self._reload_contact_list()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._reload_day_list()

    def _selected_iso(self) -> str:
        return self._month_cal.selectedDate().toString(Qt.DateFormat.ISODate)

    def _on_calendar_day_changed(self) -> None:
        self._update_date_title()
        self._update_add_button_enabled()
        self._reload_day_list()

    def _update_add_button_enabled(self) -> None:
        today = QDate.currentDate()
        ok = self._month_cal.selectedDate() >= today
        self._btn_add.setEnabled(ok)
        if ok:
            self._btn_add.setToolTip(self._lang.tr("agenda.add_tooltip_future"))
        else:
            self._btn_add.setToolTip(self._lang.tr("agenda.add_tooltip_past"))

    def _update_date_title(self) -> None:
        d = self._month_cal.selectedDate()
        loc = self._lang.qlocale()
        self._date_title.setText(
            self._lang.tr(
                "agenda.date_title",
                date=loc.toString(d, QLocale.FormatType.LongFormat),
            )
        )

    def _on_card_clicked(self, aid: int) -> None:
        self._selected_appointment_id = aid
        for cid, card in self._cards.items():
            card.set_selected(cid == aid)
        self._update_workshop_button()

    def _update_workshop_button(self) -> None:
        if not self._selected_appointment_id:
            self._btn_entry.setEnabled(False)
            return
        row = self._appointment_service.get_appointment_by_id(
            self._selected_appointment_id
        )
        if not row:
            self._btn_entry.setEnabled(False)
            return
        has_vehicle = row.get("vehicle_id") is not None
        self._btn_entry.setEnabled(has_vehicle)
        if not has_vehicle:
            self._btn_entry.setToolTip(self._lang.tr("agenda.enter_tooltip_no_vehicle"))
        else:
            self._btn_entry.setToolTip(self._lang.tr("agenda.enter_tooltip_ok"))

    def _reload_day_list(self) -> None:
        self._clear_day_cards()
        self._cards.clear()
        self._selected_appointment_id = None
        self._update_workshop_button()

        rows = self._appointment_service.get_appointments_by_date(self._selected_iso())

        if not rows:
            empty = QLabel(self._lang.tr("agenda.empty"))
            empty.setObjectName("emptyStateMuted")
            self._list_layout.addWidget(empty)
            self._list_layout.addStretch(1)
            return

        for row in rows:
            aid = int(row["id"])
            t = str(row.get("appointment_time") or "")
            client = row.get("client_name") or "—"
            plate = row.get("plate") or ""
            vm = f"{row.get('brand') or ''} {row.get('model') or ''}".strip()
            reason = row.get("reason") or ""
            card = _DayAppointmentCard(
                self._lang,
                aid,
                t,
                client,
                plate,
                vm,
                reason,
                self._list_host,
            )
            card._btn_edit.clicked.connect(
                lambda checked=False, i=aid: self._on_edit_appointment(i)
            )
            card._btn_del.clicked.connect(
                lambda checked=False, i=aid: self._on_delete_appointment(i)
            )
            card.card_clicked.connect(self._on_card_clicked)
            self._cards[aid] = card
            self._list_layout.addWidget(card)
        self._list_layout.addStretch(1)

    def _clear_day_cards(self) -> None:
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _reload_contact_list(self) -> None:
        query = self._contact_search.text().strip()
        rows = self._client_service.search_clients(query=query, limit=120)
        self._contact_list.clear()
        if not rows:
            self._contact_list.addItem(
                QListWidgetItem(self._lang.tr("agenda.contact_empty"))
            )
            return
        for row in rows:
            # sqlite3.Row supports key indexing, not dict.get()
            name = (row["name"] if row["name"] is not None else "—").strip()
            phone = (row["phone"] if row["phone"] is not None else "—").strip()
            self._contact_list.addItem(QListWidgetItem(f"{name}  ·  {phone}"))

    def _on_contact_header_clicked(self) -> None:
        self._set_contact_section_expanded(not self._contact_section_expanded)

    def _set_contact_section_expanded(self, expanded: bool) -> None:
        if expanded == self._contact_section_expanded:
            return
        self._contact_section_expanded = expanded
        self._contact_header.set_expanded(expanded)
        animate_section_height(
            self._contact_body,
            expanded,
            on_finished=self._after_contact_anim,
        )

    def _after_contact_anim(self) -> None:
        if self._contact_section_expanded:
            self._reload_contact_list()

    def _on_add_turn(self) -> None:
        d = self._month_cal.selectedDate()
        if d < QDate.currentDate():
            QMessageBox.warning(
                self,
                self._lang.tr("agenda.msg.past_title"),
                self._lang.tr("agenda.msg.past_body"),
            )
            return
        dlg = BookingDialog(
            self._appointment_service,
            self._client_service,
            self._vehicle_service,
            self._lang,
            self,
            initial_date=d,
            initial_time="09:00",
            appointment_id=None,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_day_list()

    def _on_workshop_from_turn(self) -> None:
        if not self._selected_appointment_id:
            QMessageBox.information(
                self,
                self._lang.tr("agenda.msg.pick_title"),
                self._lang.tr("agenda.msg.pick_body"),
            )
            return
        row = self._appointment_service.get_appointment_by_id(
            self._selected_appointment_id
        )
        if not row:
            return
        if row.get("vehicle_id") is None:
            QMessageBox.warning(
                self,
                self._lang.tr("agenda.msg.workshop_no_vehicle_title"),
                self._lang.tr("agenda.msg.workshop_no_vehicle_body"),
            )
            return
        oid = self._appointment_service.convert_to_order(self._selected_appointment_id)
        if oid is None:
            QMessageBox.warning(
                self,
                self._lang.tr("agenda.msg.workshop_fail_title"),
                self._lang.tr("agenda.msg.workshop_fail_body"),
            )
            return
        QMessageBox.information(
            self,
            self._lang.tr("agenda.msg.done_title"),
            self._lang.tr("agenda.msg.done_body", order_id=oid),
        )
        self._reload_day_list()

    def _on_edit_appointment(self, appointment_id: int) -> None:
        row = self._appointment_service.get_appointment_by_id(appointment_id)
        if not row:
            return
        d = QDate.fromString(str(row["appointment_date"]), Qt.DateFormat.ISODate)
        dlg = BookingDialog(
            self._appointment_service,
            self._client_service,
            self._vehicle_service,
            self._lang,
            self,
            initial_date=d,
            initial_time=str(row["appointment_time"]),
            appointment_id=appointment_id,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._reload_day_list()

    def _on_delete_appointment(self, appointment_id: int) -> None:
        r = QMessageBox.question(
            self,
            self._lang.tr("agenda.delete_title"),
            self._lang.tr("agenda.delete_question"),
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        if self._appointment_service.delete_appointment(appointment_id):
            self._reload_day_list()
