"""F5: edit a client's details and their vehicles' details."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from services.client_service import ClientService
from services.language_service import LanguageService
from services.vehicle_service import VehicleService


class ClientEditDialog(QDialog):
    """Name, phone, email and notes, plus brand/model/plate/notes of each of
    the client's vehicles. Everything is saved together, or nothing is."""

    _VEHICLE_FIELDS = ("brand", "model", "plate", "notes")

    def __init__(
        self,
        client_id: int,
        client_service: ClientService,
        vehicle_service: VehicleService,
        language_service: LanguageService,
        parent=None,
    ):
        super().__init__(parent)
        self._client_id = client_id
        self._clients = client_service
        self._lang = language_service
        self.setMinimumWidth(440)

        client = client_service.get_client_by_id(client_id)
        self._name = QLineEdit(self._text(client, "name"))
        self._phone = QLineEdit(self._text(client, "phone"))
        self._email = QLineEdit(self._text(client, "email"))
        self._notes = QLineEdit(self._text(client, "notes"))

        self._lbl_name, self._lbl_phone = QLabel(), QLabel()
        self._lbl_email, self._lbl_notes = QLabel(), QLabel()
        client_form = QFormLayout()
        client_form.addRow(self._lbl_name, self._name)
        client_form.addRow(self._lbl_phone, self._phone)
        client_form.addRow(self._lbl_email, self._email)
        client_form.addRow(self._lbl_notes, self._notes)

        # Edited values per vehicle id, kept while switching in the combo.
        self._vehicles: dict[int, dict] = {}
        for v in vehicle_service.get_vehicles_by_client(client_id):
            self._vehicles[int(v["id"])] = {
                f: str(v[f] or "") for f in self._VEHICLE_FIELDS
            }
        self._current_vehicle: int | None = None

        self._vehicle_box = QGroupBox()
        self._vehicle_combo = QComboBox()
        self._v_inputs = {f: QLineEdit() for f in self._VEHICLE_FIELDS}
        self._v_labels = {f: QLabel() for f in self._VEHICLE_FIELDS}
        self._no_vehicles = QLabel()
        vform = QFormLayout()
        vform.addRow(self._vehicle_combo)
        for f in self._VEHICLE_FIELDS:
            vform.addRow(self._v_labels[f], self._v_inputs[f])
        vbox = QVBoxLayout(self._vehicle_box)
        vbox.addWidget(self._no_vehicles)
        vbox.addLayout(vform)

        for vid, data in self._vehicles.items():
            label = " · ".join(
                p for p in (data["plate"], f"{data['brand']} {data['model']}".strip()) if p
            ) or f"#{vid}"
            self._vehicle_combo.addItem(label, vid)
        self._vehicle_combo.currentIndexChanged.connect(self._on_vehicle_changed)
        has_vehicles = bool(self._vehicles)
        self._no_vehicles.setVisible(not has_vehicles)
        self._vehicle_combo.setVisible(has_vehicles)
        for f in self._VEHICLE_FIELDS:
            self._v_inputs[f].setVisible(has_vehicles)
            self._v_labels[f].setVisible(has_vehicles)
        if has_vehicles:
            self._on_vehicle_changed(0)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(client_form)
        root.addWidget(self._vehicle_box)
        root.addWidget(buttons)
        self.apply_translations()

    @staticmethod
    def _text(row, key: str) -> str:
        if row is None or row[key] is None:
            return ""
        return str(row[key])

    def apply_translations(self) -> None:
        self.setWindowTitle(self._lang.tr("client_edit.title"))
        self._lbl_name.setText(self._lang.tr("client_edit.name"))
        self._lbl_phone.setText(self._lang.tr("client_edit.phone"))
        self._lbl_email.setText(self._lang.tr("client_edit.email"))
        self._lbl_notes.setText(self._lang.tr("client_edit.notes"))
        self._vehicle_box.setTitle(self._lang.tr("client_edit.vehicles_group"))
        self._no_vehicles.setText(self._lang.tr("client_edit.no_vehicles"))
        for f in self._VEHICLE_FIELDS:
            self._v_labels[f].setText(self._lang.tr(f"booking.{f}"))

    def _store_current_vehicle(self) -> None:
        if self._current_vehicle is not None:
            self._vehicles[self._current_vehicle] = {
                f: self._v_inputs[f].text() for f in self._VEHICLE_FIELDS
            }

    def _on_vehicle_changed(self, index: int) -> None:
        self._store_current_vehicle()
        vid = self._vehicle_combo.itemData(index)
        self._current_vehicle = int(vid) if vid is not None else None
        data = self._vehicles.get(self._current_vehicle, {})
        for f in self._VEHICLE_FIELDS:
            self._v_inputs[f].setText(data.get(f, ""))

    def _on_save(self) -> None:
        self._store_current_vehicle()
        try:
            self._clients.save_profile(
                self._client_id,
                name=self._name.text(),
                phone=self._phone.text(),
                email=self._email.text(),
                notes=self._notes.text(),
                vehicles=[{"id": vid, **data} for vid, data in self._vehicles.items()],
            )
        except ValueError as e:
            QMessageBox.warning(
                self, self._lang.tr("client_edit.save_failed"), self._lang.tr(str(e))
            )
            return
        self.accept()
