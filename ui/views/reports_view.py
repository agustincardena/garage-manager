from __future__ import annotations

from calendar import monthrange
from datetime import date

try:
    import matplotlib.pyplot as plt

    try:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    except ImportError:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

    from matplotlib.figure import Figure

    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None  # type: ignore[assignment]
    FigureCanvasQTAgg = None  # type: ignore[misc, assignment]
    Figure = None  # type: ignore[misc, assignment]
    _MATPLOTLIB_AVAILABLE = False

from PySide6.QtCore import QLocale, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.expense_service import ExpenseService
from services.income_service import IncomeService
from services.language_service import LanguageService
from services.report_service import ReportService
from ui.theme import get_theme

# Matches dashboard QGroupBox panel; integrated with Reports summary strip.
_REPORT_CHART_BG = "#1e2227"
_REPORT_CHART_GRID = "#ffffff"
_REPORT_BAR_INCOME = "#4d8aeb"
_REPORT_BAR_EXPENSE = "#e5964d"
_REPORT_BAR_EDGE_INCOME = "#355fbf"
_REPORT_BAR_EDGE_EXPENSE = "#b87638"
_REPORT_CHART_SPINE = "#4a5159"
_REPORT_CHART_LABEL_MUTED = "#b8bec9"


def _money_text(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "$ —"
    return f"$ {v:,.2f}"


class RegisterExpenseDialog(QDialog):
    """Quick expense entry with description and amount."""

    def __init__(
        self,
        language_service: LanguageService,
        parent=None,
        *,
        expense_date: str,
    ):
        super().__init__(parent)
        self._lang = language_service
        self.setMinimumWidth(400)
        self._expense_date = expense_date

        self._desc = QLineEdit()
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 9_999_999.99)
        self._amount.setDecimals(2)
        self._amount.setPrefix("$ ")
        self._amount.setValue(0.01)

        self._lbl_date = QLabel()
        self._lbl_desc = QLabel()
        self._lbl_amount = QLabel()

        form = QFormLayout()
        form.addRow(self._lbl_date, QLabel(expense_date))
        form.addRow(self._lbl_desc, self._desc)
        form.addRow(self._lbl_amount, self._amount)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setWindowTitle(self._lang.tr("reports.register_expense_title"))
        self._lbl_date.setText(self._lang.tr("reports.form_date_label"))
        self._lbl_desc.setText(self._lang.tr("reports.form_description"))
        self._lbl_amount.setText(self._lang.tr("reports.form_amount"))
        self._desc.setPlaceholderText(self._lang.tr("reports.expense_placeholder"))

    def get_values(self) -> tuple[str, float] | None:
        d = self._desc.text().strip()
        if not d:
            return None
        return d, float(self._amount.value())


class RegisterIncomeDialog(QDialog):
    """Quick manual income entry with description and amount."""

    def __init__(
        self,
        language_service: LanguageService,
        parent=None,
        *,
        income_date: str,
    ):
        super().__init__(parent)
        self._lang = language_service
        self.setMinimumWidth(400)
        self._income_date = income_date

        self._desc = QLineEdit()
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.01, 9_999_999.99)
        self._amount.setDecimals(2)
        self._amount.setPrefix("$ ")
        self._amount.setValue(0.01)

        self._lbl_date = QLabel()
        self._lbl_desc = QLabel()
        self._lbl_amount = QLabel()

        form = QFormLayout()
        form.addRow(self._lbl_date, QLabel(income_date))
        form.addRow(self._lbl_desc, self._desc)
        form.addRow(self._lbl_amount, self._amount)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(buttons)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.setWindowTitle(self._lang.tr("reports.register_income_title"))
        self._lbl_date.setText(self._lang.tr("reports.form_date_label"))
        self._lbl_desc.setText(self._lang.tr("reports.form_description"))
        self._lbl_amount.setText(self._lang.tr("reports.form_amount"))
        self._desc.setPlaceholderText(self._lang.tr("reports.income_placeholder"))

    def get_values(self) -> tuple[str, float] | None:
        d = self._desc.text().strip()
        if not d:
            return None
        return d, float(self._amount.value())


class ReportsView(QWidget):
    """Income, expenses, profit, and ledgers by month, quarter, or year."""

    def __init__(self, language_service: LanguageService, parent=None):
        super().__init__(parent)
        self._lang = language_service
        self._report_service = ReportService()
        self._expense_service = ExpenseService()
        self._income_service = IncomeService()

        self._fig = None
        self._canvas: QWidget

        today = date.today()
        header = QHBoxLayout()
        self._lbl_period = QLabel()
        header.addWidget(self._lbl_period)

        self._cb_granularity = QComboBox()
        self._cb_granularity.currentIndexChanged.connect(self._on_period_change)

        self._cb_year = QComboBox()
        for y in range(today.year - 6, today.year + 4):
            self._cb_year.addItem(str(y), y)
        self._cb_year.setCurrentIndex(
            next(i for i in range(self._cb_year.count()) if self._cb_year.itemData(i) == today.year)
        )
        self._cb_year.currentIndexChanged.connect(self._on_period_change)

        self._cb_month = QComboBox()
        self._cb_month.currentIndexChanged.connect(self._on_period_change)

        self._cb_quarter = QComboBox()
        self._cb_quarter.currentIndexChanged.connect(self._on_period_change)

        self._btn_register_income = QPushButton()
        self._btn_register_income.setObjectName("reportsRegisterIncomeBtn")
        self._btn_register_income.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_register_income.clicked.connect(self._on_register_income)

        self._btn_register_expense = QPushButton()
        self._btn_register_expense.setObjectName("reportsRegisterExpenseBtn")
        self._btn_register_expense.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_register_expense.clicked.connect(self._on_register_expense)

        header.addWidget(self._cb_granularity)
        header.addWidget(self._cb_year)
        header.addWidget(self._cb_month)
        header.addWidget(self._cb_quarter)
        header.addStretch(1)
        header.addWidget(self._btn_register_income)
        header.addWidget(self._btn_register_expense)

        self._dash = QGroupBox()
        dash_l = QHBoxLayout(self._dash)

        if _MATPLOTLIB_AVAILABLE and Figure is not None and FigureCanvasQTAgg is not None:
            self._fig = Figure(figsize=(5, 3.2), dpi=100)
            self._fig.patch.set_facecolor(_REPORT_CHART_BG)
            self._canvas = FigureCanvasQTAgg(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._canvas.setMinimumHeight(260)
        else:
            self._canvas = QLabel()
            self._canvas.setWordWrap(True)
            self._canvas.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self._canvas.setMinimumHeight(120)
            self._canvas.setObjectName("reportsMatplotlibHint")

        metrics = QVBoxLayout()
        metrics.setSpacing(16)

        self._lbl_income_title = QLabel()
        self._lbl_income_title.setObjectName("reportsMetricCaption")
        self._lbl_income = QLabel("$ 0,00")
        self._lbl_income.setObjectName("reportsMetricIncome")

        self._lbl_expense_title = QLabel()
        self._lbl_expense_title.setObjectName("reportsMetricCaption")
        self._lbl_expense = QLabel("$ 0,00")
        self._lbl_expense.setObjectName("reportsMetricExpense")

        self._lbl_profit_title = QLabel()
        self._lbl_profit_title.setObjectName("reportsMetricCaption")
        self._lbl_profit = QLabel("$ 0,00")
        self._lbl_profit.setObjectName("reportsMetricProfit")

        for w in (self._lbl_income, self._lbl_expense, self._lbl_profit):
            w.setStyleSheet(get_theme().stylesheet_profit_metric("neutral"))

        metrics.addWidget(self._lbl_income_title)
        metrics.addWidget(self._lbl_income)
        metrics.addWidget(self._lbl_expense_title)
        metrics.addWidget(self._lbl_expense)
        metrics.addWidget(self._lbl_profit_title)
        metrics.addWidget(self._lbl_profit)
        metrics.addStretch(1)

        dash_l.addWidget(self._canvas, stretch=3)
        dash_l.addLayout(metrics, stretch=2)

        detail = QWidget()
        detail_l = QHBoxLayout(detail)
        detail_l.setSpacing(16)

        self._inc_box = QGroupBox()
        inc_box_l = QVBoxLayout(self._inc_box)
        self._table_income = QTableWidget()
        self._table_income.setColumnCount(3)
        self._table_income.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table_income.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table_income.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table_income.setAlternatingRowColors(True)
        self._table_income.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        inc_box_l.addWidget(self._table_income)

        self._exp_box = QGroupBox()
        exp_box_l = QVBoxLayout(self._exp_box)
        self._table_expense = QTableWidget()
        self._table_expense.setColumnCount(3)
        self._table_expense.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table_expense.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table_expense.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table_expense.setAlternatingRowColors(True)
        self._table_expense.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        exp_box_l.addWidget(self._table_expense)

        detail_l.addWidget(self._inc_box, stretch=1)
        detail_l.addWidget(self._exp_box, stretch=1)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)
        root.addLayout(header)
        root.addWidget(self._dash)
        root.addWidget(detail, stretch=1)

        self.apply_translations()

    def _on_period_change(self, *_args) -> None:
        self._update_period_controls_visibility()
        self.refresh_reports()

    def _update_period_controls_visibility(self) -> None:
        mode = self._cb_granularity.currentData()
        self._cb_month.setVisible(mode == "monthly")
        self._cb_quarter.setVisible(mode == "quarterly")

    def _populate_granularity_combo(self) -> None:
        prev = self._cb_granularity.currentData()
        self._cb_granularity.blockSignals(True)
        self._cb_granularity.clear()
        for mode, key in (
            ("monthly", "reports.mode_monthly"),
            ("quarterly", "reports.mode_quarterly"),
            ("yearly", "reports.mode_yearly"),
        ):
            self._cb_granularity.addItem(self._lang.tr(key), mode)
        if prev is not None:
            for i in range(self._cb_granularity.count()):
                if self._cb_granularity.itemData(i) == prev:
                    self._cb_granularity.setCurrentIndex(i)
                    break
        else:
            self._cb_granularity.setCurrentIndex(0)
        self._cb_granularity.blockSignals(False)

    def _populate_quarter_combo(self) -> None:
        prev = self._cb_quarter.currentData()
        self._cb_quarter.blockSignals(True)
        self._cb_quarter.clear()
        for q in range(1, 5):
            self._cb_quarter.addItem(self._lang.tr("reports.quarter_n", q=q), q)
        if prev is not None:
            for i in range(self._cb_quarter.count()):
                if self._cb_quarter.itemData(i) == prev:
                    self._cb_quarter.setCurrentIndex(i)
                    break
        else:
            tq = (date.today().month - 1) // 3 + 1
            self._cb_quarter.setCurrentIndex(tq - 1)
        self._cb_quarter.blockSignals(False)

    def _populate_month_combo(self) -> None:
        loc = self._lang.qlocale()
        prev_m = self._cb_month.currentData()
        self._cb_month.blockSignals(True)
        self._cb_month.clear()
        for m in range(1, 13):
            self._cb_month.addItem(loc.monthName(m, QLocale.FormatType.LongFormat), m)
        if prev_m is not None:
            for i in range(self._cb_month.count()):
                if self._cb_month.itemData(i) == prev_m:
                    self._cb_month.setCurrentIndex(i)
                    break
        else:
            today = date.today()
            self._cb_month.setCurrentIndex(today.month - 1)
        self._cb_month.blockSignals(False)

    def apply_translations(self) -> None:
        self._lbl_period.setText(self._lang.tr("reports.period"))
        self._populate_granularity_combo()
        self._populate_month_combo()
        self._populate_quarter_combo()
        self._update_period_controls_visibility()
        self._btn_register_income.setText(self._lang.tr("reports.register_income"))
        self._btn_register_expense.setText(self._lang.tr("reports.register_expense"))
        self._lbl_income_title.setText(self._lang.tr("reports.metric_income"))
        self._lbl_expense_title.setText(self._lang.tr("reports.metric_expense"))
        self._lbl_profit_title.setText(self._lang.tr("reports.metric_profit"))
        cols = [
            self._lang.tr("reports.col_date"),
            self._lang.tr("reports.col_description"),
            self._lang.tr("reports.col_amount"),
        ]
        self._table_income.setHorizontalHeaderLabels(cols)
        self._table_expense.setHorizontalHeaderLabels(cols)
        if self._fig is None and isinstance(self._canvas, QLabel):
            self._canvas.setText(self._lang.tr("reports.matplotlib_missing"))
        self.refresh_reports()

    def _default_entry_date_iso(self) -> str:
        """ISO date for new income/expense rows (end of visible period unless still in progress)."""
        mode = self._cb_granularity.currentData()
        year = int(self._cb_year.currentData())
        today = date.today()
        if mode == "monthly":
            month = int(self._cb_month.currentData())
            if today.year == year and today.month == month:
                return today.isoformat()
            _, last = monthrange(year, month)
            return date(year, month, last).isoformat()
        if mode == "quarterly":
            q = int(self._cb_quarter.currentData())
            end_month = q * 3
            if today.year == year and (today.month - 1) // 3 + 1 == q:
                return today.isoformat()
            _, last_d = monthrange(year, end_month)
            return date(year, end_month, last_d).isoformat()
        if today.year == year:
            return today.isoformat()
        return date(year, 12, 31).isoformat()

    def _chart_title_for_period(self) -> str:
        mode = self._cb_granularity.currentData()
        y = int(self._cb_year.currentData())
        loc = self._lang.qlocale()
        if mode == "monthly":
            m = int(self._cb_month.currentData())
            mn = loc.monthName(m, QLocale.FormatType.LongFormat)
            return self._lang.tr("reports.chart_title_month", month=mn, year=y)
        if mode == "quarterly":
            q = int(self._cb_quarter.currentData())
            ql = self._lang.tr("reports.quarter_n", q=q)
            return self._lang.tr("reports.chart_title_quarter", quarter=ql, year=y)
        return self._lang.tr("reports.chart_title_year", year=y)

    def _apply_period_group_titles(self) -> None:
        mode = self._cb_granularity.currentData()
        if mode == "monthly":
            self._dash.setTitle(self._lang.tr("reports.summary_group_month"))
            self._inc_box.setTitle(self._lang.tr("reports.income_manual"))
            self._exp_box.setTitle(self._lang.tr("reports.expense_detail"))
        elif mode == "quarterly":
            self._dash.setTitle(self._lang.tr("reports.summary_group_quarter"))
            self._inc_box.setTitle(self._lang.tr("reports.income_manual_quarter"))
            self._exp_box.setTitle(self._lang.tr("reports.expense_detail_quarter"))
        else:
            self._dash.setTitle(self._lang.tr("reports.summary_group_year"))
            self._inc_box.setTitle(self._lang.tr("reports.income_manual_year"))
            self._exp_box.setTitle(self._lang.tr("reports.expense_detail_year"))

    def _redraw_summary_bar_chart(
        self, income: float, expenses: float, *, chart_title: str
    ) -> None:
        if not _MATPLOTLIB_AVAILABLE or self._fig is None or plt is None:
            return

        theme = get_theme()
        fg = theme.readability.groupbox_panel_text
        sans = ["Segoe UI", "Arial", "Helvetica", "DejaVu Sans", "sans-serif"]
        ctx = {
            "font.family": "sans-serif",
            "font.sans-serif": sans,
            "axes.unicode_minus": False,
            "figure.facecolor": _REPORT_CHART_BG,
            "axes.facecolor": _REPORT_CHART_BG,
            "text.color": fg,
        }

        with plt.rc_context(ctx):
            self._fig.clear()
            self._fig.patch.set_facecolor(_REPORT_CHART_BG)
            ax = self._fig.add_subplot(111)
            ax.set_facecolor(_REPORT_CHART_BG)

            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("bottom", "left"):
                ax.spines[side].set_color(_REPORT_CHART_SPINE)
                ax.spines[side].set_linewidth(0.8)

            cats = [
                self._lang.tr("reports.chart_income"),
                self._lang.tr("reports.chart_expenses"),
            ]
            vals = [income, expenses]
            colors = [_REPORT_BAR_INCOME, _REPORT_BAR_EXPENSE]
            edges = [_REPORT_BAR_EDGE_INCOME, _REPORT_BAR_EDGE_EXPENSE]

            bars = ax.bar(
                cats,
                vals,
                width=0.48,
                color=colors,
                edgecolor=edges,
                linewidth=0.9,
                zorder=2,
            )
            for patch in bars:
                patch.set_joinstyle("round")
                patch.set_capstyle("round")

            ax.tick_params(axis="both", colors=fg, labelsize=9, length=4, width=0.8)
            ax.set_ylabel(
                self._lang.tr("reports.chart_ylabel"),
                color=fg,
                fontsize=10,
                labelpad=8,
            )
            ax.set_title(
                chart_title,
                color=fg,
                fontsize=12,
                fontweight="semibold",
                pad=14,
            )

            ymax = max(vals + [1.0])
            ax.set_ylim(0, ymax * 1.14)
            ax.set_axisbelow(True)
            ax.grid(
                axis="y",
                visible=True,
                linestyle="-",
                color=_REPORT_CHART_GRID,
                alpha=0.1,
                linewidth=0.8,
                zorder=0,
            )
            ax.xaxis.grid(False)

            for b, v in zip(bars, vals):
                ax.text(
                    b.get_x() + b.get_width() / 2,
                    b.get_height(),
                    _money_text(v),
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color=_REPORT_CHART_LABEL_MUTED,
                    zorder=3,
                )

            self._fig.tight_layout(pad=1.2)
            if hasattr(self._canvas, "draw"):
                self._canvas.draw()

    def refresh_reports(self) -> None:
        mode = self._cb_granularity.currentData()
        year = int(self._cb_year.currentData())

        if mode == "monthly":
            month = int(self._cb_month.currentData())
            summary = self._report_service.get_monthly_summary(year, month)
            inc_rows = self._income_service.get_incomes_by_month(year, month)
            exp_rows = self._expense_service.get_expenses_by_month(year, month)
        elif mode == "quarterly":
            quarter = int(self._cb_quarter.currentData())
            summary = self._report_service.get_summary_by_quarter(year, quarter)
            inc_rows = self._income_service.get_incomes_by_quarter(year, quarter)
            exp_rows = self._expense_service.get_expenses_by_quarter(year, quarter)
        else:
            summary = self._report_service.get_summary_by_year(year)
            inc_rows = self._income_service.get_incomes_by_year(year)
            exp_rows = self._expense_service.get_expenses_by_year(year)

        income = float(summary.get("income") or 0)
        expenses = float(summary.get("expenses") or 0)
        profit = float(summary.get("profit") or 0)

        self._apply_period_group_titles()

        self._lbl_income.setText(_money_text(income))
        self._lbl_expense.setText(_money_text(expenses))
        self._lbl_profit.setText(_money_text(profit))
        theme = get_theme()
        if profit > 0:
            self._lbl_profit.setStyleSheet(theme.stylesheet_profit_metric("positive"))
        elif profit < 0:
            self._lbl_profit.setStyleSheet(theme.stylesheet_profit_metric("negative"))
        else:
            self._lbl_profit.setStyleSheet(theme.stylesheet_profit_metric("neutral"))

        if self._fig is not None:
            self._redraw_summary_bar_chart(
                income, expenses, chart_title=self._chart_title_for_period()
            )

        self._table_income.setRowCount(0)
        self._table_income.setRowCount(len(inc_rows))
        for r, row in enumerate(inc_rows):
            d = row["date"] if row["date"] is not None else "—"
            desc = row["description"] or "—"
            amt = row["amount"]
            self._table_income.setItem(r, 0, QTableWidgetItem(str(d)))
            self._table_income.setItem(r, 1, QTableWidgetItem(str(desc)))
            it_amt = QTableWidgetItem(_money_text(amt))
            it_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table_income.setItem(r, 2, it_amt)

        self._table_expense.setRowCount(0)
        self._table_expense.setRowCount(len(exp_rows))
        for r, row in enumerate(exp_rows):
            d = row["date"] if row["date"] is not None else "—"
            desc = row["description"] or "—"
            amt = row["amount"]
            self._table_expense.setItem(r, 0, QTableWidgetItem(str(d)))
            self._table_expense.setItem(r, 1, QTableWidgetItem(str(desc)))
            it_amt = QTableWidgetItem(_money_text(amt))
            it_amt.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table_expense.setItem(r, 2, it_amt)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh_reports()

    def _on_register_income(self) -> None:
        default_date = self._default_entry_date_iso()
        dlg = RegisterIncomeDialog(self._lang, self, income_date=default_date)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals:
            QMessageBox.warning(
                self,
                self._lang.tr("reports.msg_income_desc_title"),
                self._lang.tr("reports.msg_income_desc_body"),
            )
            return
        description, amount = vals
        try:
            self._income_service.create_income(
                description, amount, category=None, date=default_date
            )
        except Exception as e:
            QMessageBox.critical(self, self._lang.tr("common.error"), str(e))
            return
        self.refresh_reports()

    def _on_register_expense(self) -> None:
        default_date = self._default_entry_date_iso()
        dlg = RegisterExpenseDialog(self._lang, self, expense_date=default_date)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        vals = dlg.get_values()
        if not vals:
            QMessageBox.warning(
                self,
                self._lang.tr("reports.msg_expense_desc_title"),
                self._lang.tr("reports.msg_expense_desc_body"),
            )
            return
        description, amount = vals
        try:
            self._expense_service.create_expense(
                description, amount, category=None, date=default_date
            )
        except Exception as e:
            QMessageBox.critical(self, self._lang.tr("common.error"), str(e))
            return
        self.refresh_reports()
