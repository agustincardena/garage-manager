from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.appointment_service import AppointmentService
from services.client_service import ClientService
from services.language_service import LanguageService
from services.order_service import OrderService
from services.order_status import CLOSED_STATUSES, OrderStatus
from services.vehicle_service import VehicleService
from ui.formatting import format_date, format_money
from ui.views.booking_dialog import BookingDialog


class TicketCard(QFrame):
    clicked = Signal(int)

    def __init__(
        self,
        language_service: LanguageService,
        order_id: int,
        plate: str,
        client: str,
        vehicle: str,
        problem: str,
        parent=None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self._order_id = order_id
        self.setObjectName("ticketCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        lay = QVBoxLayout(self)
        lay.setSpacing(4)
        lay.setContentsMargins(14, 12, 14, 12)

        plate_l = QLabel((plate or "—").upper())
        plate_l.setObjectName("ticketPlate")

        sub = QLabel(f"{client or '—'} · {vehicle or '—'}")
        sub.setObjectName("ticketSub")
        sub.setWordWrap(True)

        self._problem_text = problem
        self._prob_label = QLabel(
            problem if problem else self._lang.tr("workshop.no_description")
        )
        self._prob_label.setObjectName("ticketProblem")
        self._prob_label.setWordWrap(True)

        lay.addWidget(plate_l)
        lay.addWidget(sub)
        lay.addWidget(self._prob_label)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._order_id)
        super().mouseReleaseEvent(event)


class CompleteOrderDialog(QDialog):
    """Close a pending order, or (``correct_order_id``) fix the amounts and
    notes of a completed one (B4)."""

    def __init__(
        self,
        language_service: LanguageService,
        parent=None,
        *,
        correct_order_id: int | None = None,
    ):
        super().__init__(parent)
        self._lang = language_service
        self._correct_order_id = correct_order_id

        self._parts = QDoubleSpinBox()
        self._parts.setRange(0, 99_999_999)
        self._parts.setDecimals(2)
        self._parts.setPrefix("$ ")
        self._parts.setValue(0)

        self._charge = QDoubleSpinBox()
        self._charge.setRange(0, 99_999_999)
        self._charge.setDecimals(2)
        self._charge.setPrefix("$ ")
        self._charge.setValue(0)

        # Decimal separator of the amounts follows the app language.
        self._parts.setLocale(language_service.qlocale())
        self._charge.setLocale(language_service.qlocale())

        self._extra = QTextEdit()
        self._extra.setMaximumHeight(90)

        self._form = QFormLayout()
        self._lbl_parts = QLabel()
        self._lbl_charge = QLabel()
        self._lbl_extra = QLabel()
        self._form.addRow(self._lbl_parts, self._parts)
        self._form.addRow(self._lbl_charge, self._charge)
        self._form.addRow(self._lbl_extra, self._extra)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(self._form)
        layout.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._correct_order_id is not None:
            self.setWindowTitle(
                self._lang.tr("workshop.correct_dialog_title", order_id=self._correct_order_id)
            )
        else:
            self.setWindowTitle(self._lang.tr("workshop.complete_dialog_title"))
        self._lbl_parts.setText(self._lang.tr("workshop.parts_spin_label"))
        self._lbl_charge.setText(self._lang.tr("workshop.charge_spin_label"))
        self._lbl_extra.setText(self._lang.tr("workshop.extra_notes_label"))
        self._extra.setPlaceholderText(self._lang.tr("workshop.extra_placeholder"))

    def accept(self):
        parts = self._parts.value()
        charge = self._charge.value()
        if charge <= 0:
            QMessageBox.warning(
                self,
                self._lang.tr("workshop.msg.charge_required_title"),
                self._lang.tr("workshop.msg.charge_required_body"),
            )
            return
        if parts < 0:
            return
        if parts == 0 and self._correct_order_id is None:
            r = QMessageBox.question(
                self,
                self._lang.tr("workshop.msg.parts_zero_title"),
                self._lang.tr("workshop.msg.parts_zero_body"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if r != QMessageBox.StandardButton.Yes:
                return
        super().accept()

    def set_values(self, parts, charge, notes) -> None:
        self._parts.setValue(float(parts or 0))
        self._charge.setValue(float(charge or 0))
        self._extra.setPlainText(notes or "")

    def get_values(self):
        return (
            self._parts.value(),
            self._charge.value(),
            self._extra.toPlainText().strip() or None,
        )


class WorkshopView(QWidget):
    def __init__(self, language_service: LanguageService, parent=None):
        super().__init__(parent)
        self._lang = language_service
        self._order_service = OrderService()

        self._ticket_cards: list[TicketCard] = []
        self._selected_order_id: int | None = None
        self._selected_card: TicketCard | None = None

        self._tabs = QTabWidget()

        self._tickets_host = QWidget()
        self._tickets_layout = QVBoxLayout(self._tickets_host)
        self._tickets_layout.setContentsMargins(8, 8, 8, 8)
        self._tickets_layout.setSpacing(10)
        self._tickets_layout.addStretch(1)

        tickets_scroll = QScrollArea()
        tickets_scroll.setWidgetResizable(True)
        tickets_scroll.setWidget(self._tickets_host)
        tickets_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._detail_plate = QLabel("—")
        self._detail_plate.setObjectName("detailPlate")
        self._detail_client = QLabel("—")
        self._detail_vehicle = QLabel("—")
        self._detail_status = QLabel("—")
        self._detail_dates = QLabel("—")
        self._detail_problem = QTextEdit()
        self._detail_problem.setReadOnly(True)
        self._detail_problem.setMaximumHeight(100)

        self._financial_box = QGroupBox()
        fin_lay = QFormLayout(self._financial_box)
        self._detail_parts = QLabel("—")
        self._detail_charge = QLabel("—")
        self._detail_completion_notes = QTextEdit()
        self._detail_completion_notes.setReadOnly(True)
        self._detail_completion_notes.setMaximumHeight(72)
        self._fin_lbl_parts = QLabel()
        self._fin_lbl_charge = QLabel()
        self._fin_lbl_notes = QLabel()
        fin_lay.addRow(self._fin_lbl_parts, self._detail_parts)
        fin_lay.addRow(self._fin_lbl_charge, self._detail_charge)
        fin_lay.addRow(self._fin_lbl_notes, self._detail_completion_notes)

        self._detail_box = QGroupBox()
        detail_form = QVBoxLayout(self._detail_box)
        self._dl_plate = QLabel()
        self._dl_client = QLabel()
        self._dl_vehicle = QLabel()
        self._dl_status = QLabel()
        self._dl_dates = QLabel()
        self._dl_problem = QLabel()
        detail_form.addWidget(self._dl_plate)
        detail_form.addWidget(self._detail_plate)
        detail_form.addWidget(self._dl_client)
        detail_form.addWidget(self._detail_client)
        detail_form.addWidget(self._dl_vehicle)
        detail_form.addWidget(self._detail_vehicle)
        detail_form.addWidget(self._dl_status)
        detail_form.addWidget(self._detail_status)
        detail_form.addWidget(self._dl_dates)
        detail_form.addWidget(self._detail_dates)
        detail_form.addWidget(self._dl_problem)
        detail_form.addWidget(self._detail_problem)
        detail_form.addWidget(self._financial_box)

        self._btn_refresh = QPushButton()
        self._btn_refresh.clicked.connect(self.refresh)

        self._btn_complete = QPushButton()
        self._btn_complete.clicked.connect(self._on_complete)
        self._btn_cancel = QPushButton()
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._btn_new_order = QPushButton()
        self._btn_new_order.clicked.connect(self._on_new_order)

        actions_top = QHBoxLayout()
        actions_top.addWidget(self._btn_refresh)
        actions_top.addStretch()
        actions_top.addWidget(self._btn_new_order)

        btn_col = QVBoxLayout()
        btn_col.addWidget(self._btn_complete)
        btn_col.addWidget(self._btn_cancel)
        btn_col.addStretch()

        pending_right = QVBoxLayout()
        pending_right.addLayout(actions_top)
        pending_right.addWidget(self._detail_box)
        pending_right.addLayout(btn_col)

        pending_split = QSplitter(Qt.Orientation.Horizontal)
        pending_split.addWidget(tickets_scroll)
        pright = QWidget()
        pright.setLayout(pending_right)
        pending_split.addWidget(pright)
        pending_split.setSizes([340, 560])

        self._tabs.addTab(pending_split, "")

        self._history_table = QTableWidget(0, 7)
        self._history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._history_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self._history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._history_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._history_table.setAlternatingRowColors(True)
        self._history_table.itemSelectionChanged.connect(self._on_history_selection)

        self._history_detail = QTextEdit()
        self._history_detail.setReadOnly(True)
        self._history_detail.setMaximumHeight(140)

        self._hist_box = QGroupBox()
        hb = QVBoxLayout(self._hist_box)
        hb.addWidget(self._history_detail)

        self._btn_correct = QPushButton()
        self._btn_correct.setEnabled(False)
        self._btn_correct.clicked.connect(self._on_correct)
        hist_actions = QHBoxLayout()
        hist_actions.addStretch()
        hist_actions.addWidget(self._btn_correct)

        hist_layout = QVBoxLayout()
        hist_layout.addWidget(self._history_table)
        hist_layout.addLayout(hist_actions)
        hist_layout.addWidget(self._hist_box)

        hist_widget = QWidget()
        hist_widget.setLayout(hist_layout)
        self._tabs.addTab(hist_widget, "")

        root = QVBoxLayout(self)
        root.addWidget(self._tabs)

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.apply_translations()
        self._refresh_tickets()
        self._refresh_history_table()
        self._clear_detail()
        self._update_action_buttons()

    def _money(self, value) -> str:
        return format_money(value, self._lang.locale_code())

    def _date(self, value) -> str:
        return format_date(value, self._lang.locale_code())

    def _status_label(self, status_key: str | None) -> str:
        if not status_key:
            return "—"
        key = f"order_status.{status_key}"
        t = self._lang.tr(key)
        return t if t != key else status_key

    def apply_translations(self) -> None:
        self._tabs.setTabText(0, self._lang.tr("workshop.tab_pending"))
        self._tabs.setTabText(1, self._lang.tr("workshop.tab_history"))
        self._detail_box.setTitle(self._lang.tr("workshop.detail_group"))
        self._dl_plate.setText(self._lang.tr("workshop.label_plate"))
        self._dl_client.setText(self._lang.tr("workshop.label_client"))
        self._dl_vehicle.setText(self._lang.tr("workshop.label_vehicle"))
        self._dl_status.setText(self._lang.tr("workshop.label_status"))
        self._dl_dates.setText(self._lang.tr("workshop.label_dates"))
        self._dl_problem.setText(self._lang.tr("workshop.label_problem"))
        self._financial_box.setTitle(self._lang.tr("workshop.financial_group"))
        self._fin_lbl_parts.setText(self._lang.tr("workshop.parts_cost"))
        self._fin_lbl_charge.setText(self._lang.tr("workshop.charge"))
        self._fin_lbl_notes.setText(self._lang.tr("workshop.completion_notes"))
        self._btn_refresh.setText(self._lang.tr("workshop.refresh"))
        self._btn_complete.setText(self._lang.tr("workshop.complete"))
        self._btn_cancel.setText(self._lang.tr("workshop.cancel_order"))
        self._btn_new_order.setText(self._lang.tr("workshop.new_order"))
        self._btn_new_order.setToolTip(self._lang.tr("workshop.new_order_tooltip"))
        self._btn_correct.setText(self._lang.tr("workshop.correct"))
        self._btn_correct.setToolTip(self._lang.tr("workshop.correct_tooltip"))
        self._hist_box.setTitle(self._lang.tr("workshop.history_summary"))
        self._history_table.setHorizontalHeaderLabels(
            [
                self._lang.tr("workshop.history_col_id"),
                self._lang.tr("workshop.history_col_closed"),
                self._lang.tr("workshop.history_col_plate"),
                self._lang.tr("workshop.history_col_client"),
                self._lang.tr("workshop.history_col_vehicle"),
                self._lang.tr("workshop.history_col_parts"),
                self._lang.tr("workshop.history_col_charge"),
            ]
        )
        self._refresh_tickets()
        self._sync_detail_after_pending_refresh()
        self._on_history_selection()

    def showEvent(self, event) -> None:
        # F1: orders created from the Agenda appear without pressing "Refresh".
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        self._refresh_tickets()
        self._refresh_history_table()
        if self._tabs.currentIndex() == 0:
            self._sync_detail_after_pending_refresh()
        else:
            self._on_history_selection()

    def _on_tab_changed(self, index: int):
        if index == 0:
            self._sync_detail_after_pending_refresh()
        else:
            self._on_history_selection()

    def _sync_detail_after_pending_refresh(self):
        ids = {c._order_id for c in self._ticket_cards}
        if self._selected_order_id is not None and self._selected_order_id in ids:
            for c in self._ticket_cards:
                if c._order_id == self._selected_order_id:
                    self._select_card(c, silent=True)
                    break
            self._load_detail(self._selected_order_id)
        else:
            self._selected_order_id = None
            self._selected_card = None
            self._clear_detail()
        self._update_action_buttons()

    def _clear_ticket_selection_style(self):
        for c in self._ticket_cards:
            c.setProperty("ticketSelected", False)
            c.style().unpolish(c)
            c.style().polish(c)

    def _select_card(self, card: TicketCard | None, silent: bool = False):
        self._clear_ticket_selection_style()
        self._selected_card = card
        if card:
            card.setProperty("ticketSelected", True)
            card.style().unpolish(card)
            card.style().polish(card)
            self._selected_order_id = card._order_id
            if not silent:
                self._load_detail(card._order_id)
                self._update_action_buttons()

    def _rebuild_tickets(self):
        while self._tickets_layout.count() > 1:
            item = self._tickets_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._ticket_cards.clear()

        orders = self._order_service.get_pending_workshop_orders()
        for o in orders:
            veh = f"{o['brand'] or ''} {o['model'] or ''}".strip() or "—"
            problem = (o["notes"] or "").strip()
            card = TicketCard(
                self._lang,
                o["id"],
                o["plate"] or "",
                o["client"] or "",
                veh,
                problem,
            )
            card.clicked.connect(self._on_ticket_clicked)
            self._tickets_layout.insertWidget(self._tickets_layout.count() - 1, card)
            self._ticket_cards.append(card)

        if not orders:
            empty = QLabel(self._lang.tr("workshop.empty_tickets"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("emptyStateMuted")
            self._tickets_layout.insertWidget(0, empty)

    def _on_ticket_clicked(self, order_id: int):
        for c in self._ticket_cards:
            if c._order_id == order_id:
                self._select_card(c)
                break

    def _refresh_tickets(self):
        self._rebuild_tickets()

    def _refresh_history_table(self):
        rows = self._order_service.get_history_orders()
        self._history_table.setRowCount(len(rows))
        for r, h in enumerate(rows):
            oid = h["id"]
            id_item = QTableWidgetItem(str(oid))
            id_item.setData(Qt.ItemDataRole.UserRole, oid)
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._history_table.setItem(r, 0, id_item)

            fecha = self._date(h["completed_at"])
            plate = h["plate"] or "—"
            client = h["client"] or "—"
            veh = f"{h['brand'] or ''} {h['model'] or ''}".strip() or "—"

            for c, text in enumerate(
                [fecha, plate, client, veh, self._money(h["parts_cost"]), self._money(h["customer_charge"])],
                start=1,
            ):
                cell = QTableWidgetItem(text)
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._history_table.setItem(r, c, cell)

        self._history_detail.clear()

    def _history_order_id_for_row(self, row: int):
        item = self._history_table.item(row, 0)
        if not item:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _selected_history_order_id(self):
        rows = self._history_table.selectionModel().selectedRows()
        if not rows:
            return None
        return self._history_order_id_for_row(rows[0].row())

    def _on_history_selection(self):
        rows = self._history_table.selectionModel().selectedRows()
        self._btn_correct.setEnabled(bool(rows))
        if not rows:
            self._history_detail.clear()
            return
        row = rows[0].row()
        oid = self._history_order_id_for_row(row)
        if oid is None:
            return
        self._load_history_detail(oid)

    def _load_history_detail(self, order_id: int):
        row = self._order_service.get_order_by_id(order_id)
        if not row:
            self._history_detail.clear()
            return
        veh = f"{(row['brand'] or '')} {(row['model'] or '')}".strip()
        lines = [
            self._lang.tr("workshop.history_line_plate", value=row["plate"] or "—"),
            self._lang.tr("workshop.history_line_client", value=row["client"] or "—"),
            self._lang.tr("workshop.history_line_vehicle", value=veh or "—"),
            self._lang.tr("workshop.history_line_problem", value=row["notes"] or "—"),
            self._lang.tr("workshop.history_line_parts", value=self._money(row["parts_cost"])),
            self._lang.tr("workshop.history_line_charge", value=self._money(row["customer_charge"])),
        ]
        if row["completion_notes"]:
            lines.append(
                self._lang.tr(
                    "workshop.history_line_notes",
                    value=row["completion_notes"],
                )
            )
        self._history_detail.setPlainText("\n".join(lines))

    def _clear_detail(self):
        self._detail_plate.setText("—")
        self._detail_client.setText("—")
        self._detail_vehicle.setText("—")
        self._detail_status.setText("—")
        self._detail_dates.setText("—")
        self._detail_problem.clear()
        self._detail_parts.setText("—")
        self._detail_charge.setText("—")
        self._detail_completion_notes.clear()
        self._financial_box.setVisible(False)

    def _load_detail(self, order_id: int):
        row = self._order_service.get_order_by_id(order_id)
        if not row:
            self._clear_detail()
            return
        self._detail_plate.setText((row["plate"] or "—").upper())
        self._detail_client.setText(row["client"] or "—")
        veh = f"{row['brand'] or ''} {row['model'] or ''}".strip() or "—"
        self._detail_vehicle.setText(veh)
        self._detail_status.setText(self._status_label(row["status"]))
        parts = []
        if row["created_at"]:
            parts.append(
                self._lang.tr("workshop.detail_line_intake", value=self._date(row["created_at"]))
            )
        if row["scheduled_date"]:
            sched = f"{self._date(row['scheduled_date'])} {row['scheduled_time'] or ''}".strip()
            parts.append(self._lang.tr("workshop.detail_line_scheduled", value=sched))
        if row["started_at"]:
            parts.append(
                self._lang.tr("workshop.detail_line_started", value=str(row["started_at"]))
            )
        if row["completed_at"]:
            parts.append(
                self._lang.tr("workshop.detail_line_closed", value=self._date(row["completed_at"]))
            )
        self._detail_dates.setText("\n".join(parts) if parts else "—")
        self._detail_problem.setPlainText(row["notes"] or "")

        sid = row["status_id"]
        if sid == OrderStatus.COMPLETED:
            self._financial_box.setVisible(True)
            self._detail_parts.setText(self._money(row["parts_cost"]))
            self._detail_charge.setText(self._money(row["customer_charge"]))
            self._detail_completion_notes.setPlainText(row["completion_notes"] or "")
        else:
            self._financial_box.setVisible(False)

    def _status_id_for_selection(self):
        if self._selected_order_id is None:
            return None
        for o in self._order_service.get_pending_workshop_orders():
            if o["id"] == self._selected_order_id:
                return o["status_id"]
        return None

    def _update_action_buttons(self):
        if self._tabs.currentIndex() != 0:
            self._btn_complete.setEnabled(False)
            self._btn_cancel.setEnabled(False)
            return
        sid = self._status_id_for_selection()
        if sid is None:
            self._btn_complete.setEnabled(False)
            self._btn_cancel.setEnabled(False)
            return
        self._btn_complete.setEnabled(sid not in CLOSED_STATUSES)
        self._btn_cancel.setEnabled(sid not in CLOSED_STATUSES)

    def _on_complete(self):
        if self._selected_order_id is None:
            return
        dlg = CompleteOrderDialog(self._lang, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        parts, charge, extra = dlg.get_values()
        try:
            self._order_service.complete_order(
                self._selected_order_id,
                parts_cost=parts,
                customer_charge=charge,
                completion_notes=extra,
            )
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("workshop.msg.cannot_close_title"),
                self._lang.tr(str(e)),
            )
            self.refresh()
            return
        except Exception as e:
            QMessageBox.critical(self, self._lang.tr("common.error"), str(e))
            return
        self._selected_order_id = None
        self._selected_card = None
        self.refresh()
        QMessageBox.information(
            self,
            self._lang.tr("workshop.msg.done_history_title"),
            self._lang.tr("workshop.msg.done_history_body"),
        )

    def _on_cancel(self):
        if self._selected_order_id is None:
            return
        r = QMessageBox.question(
            self,
            self._lang.tr("workshop.msg.cancel_title"),
            self._lang.tr("workshop.msg.cancel_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            self._order_service.cancel_order(self._selected_order_id)
        except ValueError as e:
            QMessageBox.warning(
                self,
                self._lang.tr("workshop.msg.cancel_title"),
                self._lang.tr(str(e)),
            )
            self.refresh()
            return
        self._selected_order_id = None
        self._selected_card = None
        self.refresh()

    def _on_new_order(self) -> None:
        """F3: work order for a customer who arrives without an appointment."""
        dlg = BookingDialog(
            AppointmentService(),
            ClientService(),
            VehicleService(),
            self._lang,
            self,
            initial_date=QDate.currentDate(),
            initial_time="",
            walk_in=True,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted or dlg.created_order_id is None:
            return
        self._tabs.setCurrentIndex(0)
        self._selected_order_id = dlg.created_order_id
        self.refresh()

    def _on_correct(self) -> None:
        """B4: fix the amounts/notes of a completed order, with confirmation."""
        order_id = self._selected_history_order_id()
        if order_id is None:
            return
        row = self._order_service.get_order_by_id(order_id)
        if not row:
            self.refresh()
            return
        dlg = CompleteOrderDialog(self._lang, self, correct_order_id=order_id)
        dlg.set_values(row["parts_cost"], row["customer_charge"], row["completion_notes"])
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        parts, charge, notes = dlg.get_values()
        confirm = QMessageBox.question(
            self,
            self._lang.tr("workshop.msg.correct_confirm_title"),
            self._lang.tr(
                "workshop.msg.correct_confirm_body",
                order_id=order_id,
                charge=self._money(charge),
                parts=self._money(parts),
                date=self._date(row["completed_at"]),
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._order_service.correct_completed_order(
                order_id, parts_cost=parts, customer_charge=charge, completion_notes=notes
            )
        except ValueError as e:
            QMessageBox.warning(
                self, self._lang.tr("workshop.msg.correct_failed_title"), self._lang.tr(str(e))
            )
        self._refresh_history_table()
        self._select_history_order(order_id)

    def _select_history_order(self, order_id: int) -> None:
        for r in range(self._history_table.rowCount()):
            if self._history_order_id_for_row(r) == order_id:
                self._history_table.selectRow(r)
                return
