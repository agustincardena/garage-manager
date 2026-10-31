import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from database import connection
from database.backup import BackupError, create_daily_backup
from services.language_service import LanguageService
from ui import error_handling
from ui.theme import apply_application_theme
from ui.views.agenda_view import AgendaView
from ui.views.reports_view import ReportsView
from ui.views.workshop_view import WorkshopView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._lang = LanguageService("en", self)

        self.setWindowTitle(self._lang.tr("app.window_title"))
        self.resize(1150, 720)

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 20, 12, 16)
        side_layout.setSpacing(6)

        self._brand = QLabel()
        self._brand.setObjectName("sidebarBrand")
        side_layout.addWidget(self._brand)
        side_layout.addSpacing(20)

        self._stack = QStackedWidget()
        self._workshop = WorkshopView(self._lang)
        self._agenda = AgendaView(self._lang)
        self._reports = ReportsView(self._lang)
        self._stack.addWidget(self._workshop)
        self._stack.addWidget(self._agenda)
        self._stack.addWidget(self._reports)

        self._nav_buttons: list[QPushButton] = []
        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        self._nav_keys = ("nav.workshop", "nav.agenda", "nav.reports")
        for index, _key in enumerate(self._nav_keys):
            btn = QPushButton()
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=index: self._show_section(i))
            nav_group.addButton(btn)
            side_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        side_layout.addSpacing(12)
        lang_row = QHBoxLayout()
        self._lbl_language = QLabel()
        self._cb_language = QComboBox()
        self._cb_language.addItem("English", "en")
        self._cb_language.addItem("Español", "es")
        self._cb_language.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cb_language.currentIndexChanged.connect(self._on_language_index_changed)
        lang_row.addWidget(self._lbl_language)
        lang_row.addWidget(self._cb_language, stretch=1)
        side_layout.addLayout(lang_row)

        side_layout.addStretch()

        root.addWidget(sidebar)
        root.addWidget(self._stack, stretch=1)

        self._cb_language.blockSignals(True)
        for i in range(self._cb_language.count()):
            if self._cb_language.itemData(i) == self._lang.locale_code():
                self._cb_language.setCurrentIndex(i)
                break
        self._cb_language.blockSignals(False)

        self._lang.language_changed.connect(self._on_language_changed)
        self._apply_translations()
        self._show_section(0)

    def language_service(self) -> LanguageService:
        return self._lang

    def _on_language_index_changed(self, index: int) -> None:
        code = self._cb_language.itemData(index)
        if code:
            self._lang.set_locale(code)

    def _on_language_changed(self, code: str) -> None:
        self._sync_language_combo(code)
        self._apply_translations()

    def _sync_language_combo(self, code: str) -> None:
        self._cb_language.blockSignals(True)
        for i in range(self._cb_language.count()):
            if self._cb_language.itemData(i) == code:
                self._cb_language.setCurrentIndex(i)
                break
        self._cb_language.blockSignals(False)

    def _apply_translations(self) -> None:
        self.setWindowTitle(self._lang.tr("app.window_title"))
        self._brand.setText(self._lang.tr("app.brand"))
        for btn, key in zip(self._nav_buttons, self._nav_keys):
            btn.setText(self._lang.tr(key))
        self._workshop.apply_translations()
        self._agenda.apply_translations()
        self._reports.apply_translations()

    def _show_section(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        if 0 <= index < len(self._nav_buttons):
            self._nav_buttons[index].setChecked(True)


def _run_startup_backup() -> BackupError | None:
    """Back up the database once per day. A failure must not block the app."""
    try:
        create_daily_backup(connection.db_path)
    except BackupError as exc:
        logging.getLogger(__name__).error("Startup backup failed", exc_info=True)
        return exc
    return None


def main() -> None:
    app = QApplication(sys.argv)

    log_path = error_handling.setup_logging(connection.get_user_data_dir())
    error_handling.install_excepthook()
    logging.getLogger(__name__).info(
        "Garage Manager starting (database: %s, log: %s)", connection.db_path, log_path
    )
    # Before the first database connection, so the copy reflects the data
    # as it was before any migration runs.
    backup_error = _run_startup_backup()

    apply_application_theme(app)

    win = MainWindow()
    lang = win.language_service()
    error_handling.set_translator(lang.tr)
    win.show()

    if backup_error is not None:
        QMessageBox.warning(
            win,
            lang.tr("backup.failed_title"),
            lang.tr("backup.failed_body", error=str(backup_error), log_path=str(log_path)),
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
