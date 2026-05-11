from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.appointment_service import AppointmentService, _parse_time_to_minutes
from services.client_service import ClientService
from services.language_service import LanguageService
from services.vehicle_service import VehicleService
from ui.widgets.collapsible_header import SectionHeaderBar, animate_section_height


class BookingDialog(QDialog):
    """Create or edit an appointment: client, vehicle, date/time, reason."""

    def __init__(
        self,
        appointment_service: AppointmentService,
        client_service: ClientService,
        vehicle_service: VehicleService,
        language_service: LanguageService,
        parent=None,
        *,
        initial_date: QDate,
        initial_time: str,
        appointment_id: int | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("bookingDialog")
        self._appt = appointment_service
        self._clients = client_service
        self._vehicles = vehicle_service
        self._lang = language_service
        self._appointment_id = appointment_id
        self._selected_client_id: int | None = None
        self._selected_vehicle_id: int | None = None
        self._selected_client_name: str = ""
        self._client_list_expanded = True
        self._client_section_expanded = True
        self._vehicle_section_expanded = False
        self._vehicle_did_auto_expand_once = False

        self._date_edit = QDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("yyyy-MM-dd")
        self._time_edit = QLineEdit()
        self._time_edit.setPlaceholderText(self._lang.tr("booking.time_placeholder"))

        self._reason = QTextEdit()
        self._reason.setMaximumHeight(72)

        self._rb_existing = QRadioButton()
        self._rb_new = QRadioButton()
        self._rb_existing.setChecked(True)

        self._client_search = QLineEdit()
        self._client_list = QListWidget()
        self._client_list.setObjectName("bookingDialogClientList")
        self._client_list.setFrameShape(QFrame.Shape.NoFrame)
        self._client_list.setMaximumHeight(160)
        self._client_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self._new_first = QLineEdit()
        self._new_last = QLineEdit()
        self._new_phone = QLineEdit()

        self._vehicle_combo = QComboBox()
        self._vehicle_all = QCheckBox()
        self._btn_transfer = QPushButton()
        self._v_brand = QLineEdit()
        self._v_model = QLineEdit()
        self._v_plate = QLineEdit()
        self._v_notes = QLineEdit()

        self._client_widget = QWidget()
        self._new_client_widget = QWidget()

        self._dt_card = QFrame()
        self._dt_card.setObjectName("bookingFormSection")
        self._dt_section_label = QLabel()
        self._dt_section_label.setObjectName("bookingSectionLabel")
        self._lbl_date = QLabel()
        self._lbl_time = QLabel()
        dt_lay = QVBoxLayout(self._dt_card)
        dt_lay.setContentsMargins(0, 0, 0, 0)
        dt_lay.setSpacing(8)
        dt_lay.addWidget(self._dt_section_label)
        fl = QFormLayout()
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(10)
        fl.addRow(self._lbl_date, self._date_edit)
        fl.addRow(self._lbl_time, self._time_edit)
        dt_lay.addLayout(fl)

        self._rg_card = QFrame()
        self._rg_card.setObjectName("bookingFormSection")
        self._rg_section_label = QLabel()
        self._rg_section_label.setObjectName("bookingSectionLabel")
        rg_lay = QVBoxLayout(self._rg_card)
        rg_lay.setContentsMargins(0, 0, 0, 0)
        rg_lay.setSpacing(8)
        rg_lay.addWidget(self._rg_section_label)
        rg_lay.addWidget(self._reason)

        self._client_card = QFrame()
        self._client_card.setObjectName("bookingCollapsibleCard")
        cgl = QVBoxLayout(self._client_card)
        cgl.setContentsMargins(0, 0, 0, 0)
        cgl.setSpacing(0)
        self._btn_change_client = QPushButton()
        self._btn_change_client.setObjectName("bookingGhostLink")
        self._btn_change_client.setFlat(True)
        self._btn_change_client.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_change_client.clicked.connect(self._on_change_client)
        self._btn_change_client.hide()

        self._client_section_header = SectionHeaderBar()
        self._client_section_header.clicked.connect(self._on_client_header_clicked)
        self._client_body = QWidget()
        client_body_lay = QVBoxLayout(self._client_body)
        client_body_lay.setContentsMargins(0, 8, 0, 0)
        client_body_lay.setSpacing(8)
        rowc = QHBoxLayout()
        rowc.addWidget(self._rb_existing)
        rowc.addWidget(self._rb_new)
        client_body_lay.addLayout(rowc)
        client_body_lay.addWidget(self._client_widget)
        client_body_lay.addWidget(self._new_client_widget)
        cgl.addWidget(self._client_section_header)
        cgl.addWidget(self._client_body)

        self._vehicle_card = QFrame()
        self._vehicle_card.setObjectName("bookingCollapsibleCard")
        vgl = QVBoxLayout(self._vehicle_card)
        vgl.setContentsMargins(0, 0, 0, 0)
        vgl.setSpacing(0)
        self._vehicle_section_header = SectionHeaderBar()
        self._vehicle_section_header.clicked.connect(self._on_vehicle_header_clicked)
        self._vehicle_body = QWidget()
        vehicle_body_lay = QVBoxLayout(self._vehicle_body)
        vehicle_body_lay.setContentsMargins(0, 8, 0, 0)
        vehicle_body_lay.setSpacing(8)
        vehicle_body_lay.addWidget(self._vehicle_combo)
        vehicle_body_lay.addWidget(self._vehicle_all)
        self._lbl_brand = QLabel()
        self._lbl_model = QLabel()
        self._lbl_plate = QLabel()
        self._lbl_vnotes = QLabel()
        nf = QGridLayout()
        nf.addWidget(self._lbl_brand, 0, 0)
        nf.addWidget(self._v_brand, 0, 1)
        nf.addWidget(self._lbl_model, 1, 0)
        nf.addWidget(self._v_model, 1, 1)
        nf.addWidget(self._lbl_plate, 2, 0)
        nf.addWidget(self._v_plate, 2, 1)
        nf.addWidget(self._lbl_vnotes, 3, 0)
        nf.addWidget(self._v_notes, 3, 1)
        vehicle_body_lay.addLayout(nf)
        vehicle_body_lay.addWidget(self._btn_transfer)
        vgl.addWidget(self._vehicle_section_header)
        vgl.addWidget(self._vehicle_body)

        self._lbl_first = QLabel()
        self._lbl_last = QLabel()
        self._lbl_phone = QLabel()

        self._build_client_panels()
        self._wire()
        self._apply_initial_datetime(initial_date, initial_time)

        if appointment_id:
            self._load_existing(appointment_id)
        else:
            self._refresh_client_list()
            self._refresh_vehicle_combo()

        self._setup_date_limits()

        self._vehicle_section_header.set_expanded(False)
        self._vehicle_body.setVisible(False)

        content = QWidget()
        content.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding
        )
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        content_layout.addWidget(self._dt_card)
        content_layout.addWidget(self._rg_card)
        content_layout.addWidget(self._client_card)
        content_layout.addWidget(self._vehicle_card)
        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._footer = QFrame()
        self._footer.setObjectName("bookingDialogFooter")
        foot_lay = QHBoxLayout(self._footer)
        foot_lay.setContentsMargins(16, 12, 16, 12)
        foot_lay.setSpacing(12)
        foot_lay.addStretch(1)
        self._btn_cancel = QPushButton()
        self._btn_cancel.setObjectName("bookingDialogCancelBtn")
        self._btn_save = QPushButton()
        self._btn_save.setObjectName("bookingDialogSaveBtn")
        self._btn_save.setDefault(True)
        self._btn_save.setAutoDefault(True)
        self._btn_cancel.clicked.connect(self.reject)
        self._btn_save.clicked.connect(self._on_save)
        foot_lay.addWidget(self._btn_cancel)
        foot_lay.addWidget(self._btn_save)

        main = QVBoxLayout(self)
        main.setContentsMargins(15, 15, 15, 0)
        main.setSpacing(0)
        main.addWidget(scroll, stretch=1)
        main.addWidget(self._footer)

        self._apply_dialog_size_limits()
        self.setMinimumWidth(440)

        self._toggle_client_mode()
        self.apply_translations()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.apply_translations()
        self._center_on_parent_window()

    def _apply_dialog_size_limits(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        ag = screen.availableGeometry()
        self.setMaximumSize(
            max(self.minimumWidth(), int(ag.width() * 0.95)),
            int(ag.height() * 0.92),
        )

    def _center_on_parent_window(self) -> None:
        ref = self.parentWidget()
        win = ref.window() if ref is not None else None
        if win is None:
            return
        dlg_geo = self.frameGeometry()
        dlg_geo.moveCenter(win.frameGeometry().center())
        self.move(dlg_geo.topLeft())

    def apply_translations(self) -> None:
        self.setWindowTitle(
            self._lang.tr("booking.title_edit")
            if self._appointment_id
            else self._lang.tr("booking.title_new")
        )
        self._dt_section_label.setText(self._lang.tr("booking.datetime_group"))
        self._rg_section_label.setText(self._lang.tr("booking.reason_group"))
        self._lbl_date.setText(self._lang.tr("booking.date_label"))
        self._lbl_time.setText(self._lang.tr("booking.time_label"))
        self._time_edit.setPlaceholderText(self._lang.tr("booking.time_placeholder"))
        self._reason.setPlaceholderText(self._lang.tr("booking.reason_placeholder"))
        self._rb_existing.setText(self._lang.tr("booking.existing_client"))
        self._rb_new.setText(self._lang.tr("booking.new_client"))
        self._client_search.setPlaceholderText(self._lang.tr("booking.search_placeholder"))
        self._refresh_client_header()
        self._lbl_first.setText(self._lang.tr("booking.first_name"))
        self._lbl_last.setText(self._lang.tr("booking.last_name"))
        self._lbl_phone.setText(self._lang.tr("booking.phone"))
        self._vehicle_all.setText(self._lang.tr("booking.see_all_vehicles"))
        self._btn_transfer.setText(self._lang.tr("booking.transfer_btn"))
        self._btn_transfer.setToolTip(self._lang.tr("booking.transfer_tooltip"))
        self._lbl_brand.setText(self._lang.tr("booking.brand"))
        self._lbl_model.setText(self._lang.tr("booking.model"))
        self._lbl_plate.setText(self._lang.tr("booking.plate"))
        self._lbl_vnotes.setText(self._lang.tr("booking.notes"))
        self._v_plate.setPlaceholderText(self._lang.tr("booking.license_placeholder"))
        self._v_notes.setPlaceholderText(self._lang.tr("booking.vehicle_notes_placeholder"))
        self._btn_save.setText(self._lang.tr("booking.save"))
        self._btn_cancel.setText(self._lang.tr("booking.cancel"))
        self._btn_change_client.setText(self._lang.tr("booking.change_client"))
        self._refresh_vehicle_combo()
        self._refresh_vehicle_header()

    def _build_client_panels(self) -> None:
        ex = QVBoxLayout(self._client_widget)
        ex.setContentsMargins(0, 0, 0, 0)
        ex.setSpacing(8)
        ex.addWidget(self._client_search)
        ex.addWidget(self._btn_change_client)
        ex.addWidget(self._client_list)

        nc = QFormLayout(self._new_client_widget)
        nc.addRow(self._lbl_first, self._new_first)
        nc.addRow(self._lbl_last, self._new_last)
        nc.addRow(self._lbl_phone, self._new_phone)

    def _wire(self) -> None:
        self._rb_existing.toggled.connect(self._toggle_client_mode)
        self._rb_new.toggled.connect(self._toggle_client_mode)
        self._client_search.textChanged.connect(self._on_client_search_changed)
        self._client_list.itemClicked.connect(self._on_client_clicked)
        self._vehicle_combo.currentIndexChanged.connect(self._on_vehicle_combo)
        self._vehicle_all.toggled.connect(self._refresh_vehicle_combo)
        self._btn_transfer.clicked.connect(self._on_transfer_vehicle)
        self._new_first.textChanged.connect(self._on_new_client_field_changed)
        self._new_last.textChanged.connect(self._on_new_client_field_changed)
        self._new_phone.textChanged.connect(self._on_new_client_field_changed)

    def _apply_initial_datetime(self, d: QDate, t: str) -> None:
        self._time_edit.setText(t.strip() if t else "08:00")
        if self._appointment_id:
            return
        today = QDate.currentDate()
        self._date_edit.setDate(d if d >= today else today)

    def _setup_date_limits(self) -> None:
        today = QDate.currentDate()
        if self._appointment_id:
            row = self._appt.get_appointment_by_id(self._appointment_id)
            if not row:
                self._date_edit.setMinimumDate(today)
                return
            ad = QDate.fromString(
                str(row["appointment_date"]), Qt.DateFormat.ISODate
            )
            self._date_edit.setMinimumDate(ad if ad < today else today)
        else:
            self._date_edit.setMinimumDate(today)

    def _validate_form(self) -> bool:
        today = QDate.currentDate()
        if not self._appointment_id and self._date_edit.date() < today:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.past_title"),
                self._lang.tr("booking.msg.past_body"),
            )
            return False
        tm = self._time_edit.text().strip()
        if not tm:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.time_required_title"),
                self._lang.tr("booking.msg.time_required_body"),
            )
            return False
        try:
            _parse_time_to_minutes(tm)
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.time_invalid_title"),
                self._lang.tr(str(e)),
            )
            return False
        return True

    def _on_client_search_changed(self) -> None:
        if (
            self._rb_existing.isChecked()
            and self._selected_client_id
            and not self._client_list_expanded
        ):
            self._client_list_expanded = True
            self._sync_client_picker_visibility()
        self._refresh_client_list()

    def _sync_client_picker_visibility(self) -> None:
        ex = self._rb_existing.isChecked()
        sec = self._client_section_expanded
        if sec and ex:
            self._client_search.setVisible(True)
            self._client_list.setVisible(self._client_list_expanded)
            self._btn_change_client.setVisible(
                bool(self._selected_client_id) and not self._client_list_expanded
            )
        else:
            self._btn_change_client.hide()

    def _toggle_client_mode(self) -> None:
        ex = self._rb_existing.isChecked()
        sec = self._client_section_expanded
        self._client_widget.setVisible(sec and ex)
        self._new_client_widget.setVisible(sec and not ex)
        self._sync_client_picker_visibility()
        if ex:
            self._refresh_client_list()
        else:
            self._selected_client_id = None
            self._selected_client_name = ""
            self._client_list_expanded = True
            self._refresh_vehicle_combo()
            self._maybe_reset_vehicle_after_client_lost()
        self._refresh_client_header()
        self._adjust_dialog_height()

    def _refresh_client_list(self) -> None:
        self._client_list.blockSignals(True)
        self._client_list.clear()
        q = self._client_search.text()
        rows = self._clients.search_clients(q, limit=100)
        for row in rows:
            item = QListWidgetItem(row["name"] or "—")
            item.setData(Qt.ItemDataRole.UserRole, int(row["id"]))
            item.setData(Qt.ItemDataRole.UserRole + 1, (row["name"] or "—").strip())
            extra = row["phone"] or row["email"] or ""
            if extra:
                item.setToolTip(extra)
            self._client_list.addItem(item)
        if self._selected_client_id:
            for i in range(self._client_list.count()):
                it = self._client_list.item(i)
                if it.data(Qt.ItemDataRole.UserRole) == self._selected_client_id:
                    self._client_list.setCurrentItem(it)
                    self._selected_client_name = (
                        it.data(Qt.ItemDataRole.UserRole + 1) or "—"
                    )
                    break
        self._client_list.blockSignals(False)
        if self._rb_existing.isChecked() and self._selected_client_id:
            self._refresh_vehicle_combo()
        self._refresh_client_header()
        self._sync_client_picker_visibility()

    def _on_client_clicked(self, item: QListWidgetItem) -> None:
        self._selected_client_id = int(item.data(Qt.ItemDataRole.UserRole))
        self._selected_client_name = item.data(Qt.ItemDataRole.UserRole + 1) or "—"
        if not self._vehicle_all.isChecked():
            self._refresh_vehicle_combo()
        self._set_client_list_expanded(False)
        self._maybe_auto_expand_vehicle()

    def _refresh_vehicle_combo(self) -> None:
        self._vehicle_combo.blockSignals(True)
        self._vehicle_combo.clear()
        self._vehicle_combo.addItem(self._lang.tr("booking.vehicle_combo_new"), -1)

        if self._vehicle_all.isChecked():
            rows = self._vehicles.get_all_vehicles()
            for row in rows:
                vid = int(row["id"])
                plate = (row["plate"] or "—").upper()
                who = row["client_name"] or "—"
                label = (
                    f"{plate} · {row['brand'] or ''} {row['model'] or ''} ({who})"
                ).strip()
                self._vehicle_combo.addItem(label, vid)
        elif self._selected_client_id:
            rows = self._vehicles.get_vehicles_by_client(self._selected_client_id)
            for row in rows:
                vid = int(row["id"])
                plate = (row["plate"] or "—").upper()
                label = (f"{plate} · {row['brand'] or ''} {row['model'] or ''}").strip()
                self._vehicle_combo.addItem(label, vid)
        self._vehicle_combo.blockSignals(False)
        self._sync_vehicle_selection()
        self._refresh_vehicle_header()

    def _sync_vehicle_selection(self) -> None:
        if self._selected_vehicle_id is None:
            self._vehicle_combo.setCurrentIndex(0)
            self._set_new_vehicle_fields_enabled(True)
            return
        for i in range(self._vehicle_combo.count()):
            if self._vehicle_combo.itemData(i) == self._selected_vehicle_id:
                self._vehicle_combo.setCurrentIndex(i)
                self._set_new_vehicle_fields_enabled(False)
                return
        self._vehicle_combo.setCurrentIndex(0)
        self._set_new_vehicle_fields_enabled(True)

    def _on_vehicle_combo(self) -> None:
        data = self._vehicle_combo.currentData()
        if data == -1:
            self._selected_vehicle_id = None
            self._set_new_vehicle_fields_enabled(True)
        else:
            self._selected_vehicle_id = int(data)
            self._set_new_vehicle_fields_enabled(False)
        self._refresh_vehicle_header()

    def _set_new_vehicle_fields_enabled(self, on: bool) -> None:
        for w in (self._v_brand, self._v_model, self._v_plate, self._v_notes):
            w.setEnabled(on)

    def _load_existing(self, appointment_id: int) -> None:
        row = self._appt.get_appointment_by_id(appointment_id)
        if not row:
            return
        self._date_edit.setDate(
            QDate.fromString(str(row["appointment_date"]), Qt.DateFormat.ISODate)
        )
        self._time_edit.setText(str(row["appointment_time"]))
        self._reason.setPlainText(row["reason"] if row["reason"] is not None else "")

        self._selected_client_id = int(row["client_id"])
        self._selected_vehicle_id = (
            int(row["vehicle_id"]) if row["vehicle_id"] is not None else None
        )

        self._rb_existing.setChecked(True)
        self._refresh_client_list()
        self._refresh_vehicle_combo()
        self._set_client_list_expanded(False)
        self._vehicle_did_auto_expand_once = True
        self._vehicle_section_expanded = False
        self._vehicle_section_header.set_expanded(False)
        self._vehicle_body.setVisible(False)
        if self._selected_vehicle_id:
            for i in range(self._vehicle_combo.count()):
                if self._vehicle_combo.itemData(i) == self._selected_vehicle_id:
                    self._vehicle_combo.setCurrentIndex(i)
                    break
        self._sync_client_picker_visibility()
        self._refresh_client_header()
        self._refresh_vehicle_header()
        self._adjust_dialog_height()

    def _resolve_client_id(self) -> int | None:
        if self._rb_existing.isChecked():
            if not self._selected_client_id:
                QMessageBox.warning(
                    self,
                    self._lang.tr("booking.msg.pick_client_title"),
                    self._lang.tr("booking.msg.pick_client_body"),
                )
                return None
            return self._selected_client_id
        first = self._new_first.text().strip()
        last = self._new_last.text().strip()
        phone = self._new_phone.text().strip()
        if not first or not last or not phone:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.new_client_fields_title"),
                self._lang.tr("booking.msg.new_client_fields_body"),
            )
            return None
        name = f"{first} {last}".strip()
        return self._clients.create_client(name=name, phone=phone)

    def _maybe_reassign_vehicle(self, vehicle_id: int, target_client_id: int) -> bool:
        row = self._vehicles.get_vehicle_by_id(vehicle_id)
        if not row:
            return False
        vid_cid = int(row["client_id"])
        if vid_cid == target_client_id:
            return True
        ret = QMessageBox.question(
            self,
            self._lang.tr("booking.msg.reassign_title"),
            self._lang.tr("booking.msg.reassign_body"),
        )
        if ret != QMessageBox.StandardButton.Yes:
            return False
        self._vehicles.assign_vehicle_to_client(vehicle_id, target_client_id)
        return True

    def _resolve_vehicle_id(self, client_id: int) -> tuple[bool, int | None]:
        data = self._vehicle_combo.currentData()
        if data is None:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.pick_vehicle_title"),
                self._lang.tr("booking.msg.pick_vehicle_body"),
            )
            return False, None
        if data == -1:
            return self._create_new_vehicle(client_id)
        vid = int(data)
        if not self._maybe_reassign_vehicle(vid, client_id):
            return False, None
        return True, vid

    def _create_new_vehicle(self, client_id: int) -> tuple[bool, int | None]:
        plate = self._v_plate.text().strip().upper()
        if not plate:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.plate_required_title"),
                self._lang.tr("booking.msg.plate_required_body"),
            )
            return False, None
        existing = self._vehicles.get_vehicle_by_plate(plate)
        if existing:
            vid = int(existing["id"])
            if not self._maybe_reassign_vehicle(vid, client_id):
                return False, None
            return True, vid
        try:
            new_id = self._vehicles.create_vehicle(
                client_id,
                brand=self._v_brand.text().strip() or None,
                model=self._v_model.text().strip() or None,
                plate=plate,
                notes=self._v_notes.text().strip() or None,
            )
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.pick_vehicle_title"),
                self._lang.tr(str(e)),
            )
            return False, None
        return True, new_id

    def _on_transfer_vehicle(self) -> None:
        if not self._selected_client_id:
            QMessageBox.information(
                self,
                self._lang.tr("booking.msg.transfer_pick_client_title"),
                self._lang.tr("booking.msg.transfer_pick_client_body"),
            )
            return
        data = self._vehicle_combo.currentData()
        if data in (None, -1):
            QMessageBox.information(
                self,
                self._lang.tr("booking.msg.transfer_pick_vehicle_title"),
                self._lang.tr("booking.msg.transfer_pick_vehicle_body"),
            )
            return
        try:
            self._vehicles.assign_vehicle_to_client(int(data), self._selected_client_id)
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.transfer_pick_vehicle_title"),
                self._lang.tr(str(e)),
            )
            return
        QMessageBox.information(
            self,
            self._lang.tr("booking.msg.transfer_done_title"),
            self._lang.tr("booking.msg.transfer_done_body"),
        )
        self._selected_vehicle_id = int(data)
        self._refresh_vehicle_combo()

    def _on_save(self) -> None:
        if not self._validate_form():
            return
        client_id = self._resolve_client_id()
        if not client_id:
            return
        ok, vehicle_id = self._resolve_vehicle_id(client_id)
        if not ok:
            return
        ds = self._date_edit.date().toString(Qt.DateFormat.ISODate)
        tm = self._time_edit.text().strip()
        reason = self._reason.toPlainText().strip() or None
        try:
            if self._appointment_id:
                kw = dict(
                    client_id=client_id,
                    vehicle_id=vehicle_id,
                    appointment_date=ds,
                    appointment_time=tm,
                    reason=reason,
                )
                self._appt.update_appointment(self._appointment_id, **kw)
            else:
                self._appt.create_appointment(
                    client_id,
                    vehicle_id,
                    ds,
                    tm,
                    reason=reason,
                )
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("booking.msg.time_required_title"),
                self._lang.tr(str(e)),
            )
            return
        self.accept()

    def _on_client_header_clicked(self) -> None:
        self._set_client_section_expanded(not self._client_section_expanded)

    def _on_vehicle_header_clicked(self) -> None:
        self._set_vehicle_section_expanded(not self._vehicle_section_expanded)

    def _set_client_section_expanded(self, expanded: bool) -> None:
        if expanded == self._client_section_expanded:
            return
        self._client_section_expanded = expanded
        self._client_section_header.set_expanded(expanded)
        self._refresh_client_header()
        if expanded:
            self._toggle_client_mode()

        def _after() -> None:
            if not expanded:
                self._toggle_client_mode()
            self._adjust_dialog_height()

        animate_section_height(self._client_body, expanded, on_finished=_after)

    def _set_vehicle_section_expanded(self, expanded: bool) -> None:
        if expanded == self._vehicle_section_expanded:
            return
        self._vehicle_section_expanded = expanded
        self._vehicle_section_header.set_expanded(expanded)
        self._refresh_vehicle_header()

        def _after() -> None:
            self._adjust_dialog_height()

        animate_section_height(self._vehicle_body, expanded, on_finished=_after)

    def _refresh_client_header(self) -> None:
        self._client_section_header.set_title(self._lang.tr("booking.client_group"))
        self._client_section_header.set_expanded(self._client_section_expanded)
        sub: str | None = None
        if not self._client_section_expanded:
            if self._rb_existing.isChecked() and self._selected_client_name:
                sub = self._lang.tr(
                    "booking.client_selected_summary",
                    name=self._selected_client_name,
                )
            elif not self._rb_existing.isChecked():
                fn = self._new_first.text().strip()
                ln = self._new_last.text().strip()
                label = f"{fn} {ln}".strip()
                sub = label if label else self._lang.tr("booking.new_client")
            elif self._rb_existing.isChecked():
                sub = self._lang.tr("booking.client_collapsed_hint")
        elif (
            self._client_section_expanded
            and self._rb_existing.isChecked()
            and self._selected_client_id
            and not self._client_list_expanded
            and self._selected_client_name
        ):
            sub = self._lang.tr(
                "booking.client_selected_summary",
                name=self._selected_client_name,
            )
        self._client_section_header.set_subtitle(sub)

    def _refresh_vehicle_header(self) -> None:
        self._vehicle_section_header.set_title(self._lang.tr("booking.vehicle_group"))
        self._vehicle_section_header.set_expanded(self._vehicle_section_expanded)
        if not self._vehicle_section_expanded:
            txt = self._vehicle_combo.currentText().strip()
            new_lbl = self._lang.tr("booking.vehicle_combo_new")
            if txt and txt != new_lbl:
                self._vehicle_section_header.set_subtitle(txt)
            else:
                self._vehicle_section_header.set_subtitle(None)
        else:
            self._vehicle_section_header.set_subtitle(None)

    def _set_client_list_expanded(self, expanded: bool) -> None:
        self._client_list_expanded = expanded
        self._sync_client_picker_visibility()
        self._refresh_client_header()
        self._adjust_dialog_height()

    def _on_change_client(self) -> None:
        self._set_client_list_expanded(True)
        self._client_search.setFocus(Qt.FocusReason.OtherFocusReason)

    def _client_ready_for_vehicle(self) -> bool:
        if self._rb_existing.isChecked():
            return self._selected_client_id is not None
        f = self._new_first.text().strip()
        l = self._new_last.text().strip()
        p = self._new_phone.text().strip()
        return bool(f and l and p)

    def _maybe_auto_expand_vehicle(self) -> None:
        if self._appointment_id:
            return
        if self._vehicle_did_auto_expand_once:
            return
        if not self._client_ready_for_vehicle():
            return
        self._vehicle_did_auto_expand_once = True
        if not self._vehicle_section_expanded:
            self._set_vehicle_section_expanded(True)

    def _maybe_reset_vehicle_after_client_lost(self) -> None:
        if self._appointment_id:
            return
        self._vehicle_did_auto_expand_once = False
        if self._vehicle_section_expanded:
            self._set_vehicle_section_expanded(False)

    def _on_new_client_field_changed(self) -> None:
        self._refresh_client_header()
        self._maybe_auto_expand_vehicle()

    def _adjust_dialog_height(self) -> None:
        self.adjustSize()
