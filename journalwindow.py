# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QLabel,
)
from PyQt6.QtCore import QDate, Qt
from journalwindowbackend import JournalWindowBackend
from removecategorydialog import RemoveCategoryDialog


class JournalWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.backend = JournalWindowBackend()
        self.stack = stack

        self.setWindowTitle("Muntenman Journaal")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        # ── Return button ──────────────────────────────────────────────────
        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

        # ── Filter group ───────────────────────────────────────────────────
        filter_group = QGroupBox("Filters")
        filter_grid = QGridLayout()
        filter_grid.setHorizontalSpacing(12)
        filter_grid.setVerticalSpacing(6)

        filter_grid.addWidget(QLabel("Reference:"), 0, 0)
        self.filter_reference = QLineEdit()
        self.filter_reference.setPlaceholderText("Search…")
        self.filter_reference.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_reference, 0, 1)

        filter_grid.addWidget(QLabel("Crdt/Dbt:"), 0, 2)
        self.filter_cdt_dbt = QComboBox()
        self.filter_cdt_dbt.addItems(["All", "CRDT", "DBIT"])
        self.filter_cdt_dbt.currentIndexChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_cdt_dbt, 0, 3)

        filter_grid.addWidget(QLabel("Category:"), 0, 4)
        self.filter_category = QComboBox()
        self.filter_category.addItem("All")
        self.filter_category.currentIndexChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_category, 0, 5)

        filter_grid.addWidget(QLabel("Counterparty:"), 1, 0)
        self.filter_counterparty = QLineEdit()
        self.filter_counterparty.setPlaceholderText("Search…")
        self.filter_counterparty.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_counterparty, 1, 1)

        filter_grid.addWidget(QLabel("Description:"), 1, 2)
        self.filter_description = QLineEdit()
        self.filter_description.setPlaceholderText("Search…")
        self.filter_description.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_description, 1, 3, 1, 3)

        filter_grid.addWidget(QLabel("Amount min:"), 2, 0)
        self.filter_amount_min = QDoubleSpinBox()
        self.filter_amount_min.setRange(0, 999_999_999)
        self.filter_amount_min.setDecimals(2)
        self.filter_amount_min.setValue(0)
        self.filter_amount_min.valueChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_amount_min, 2, 1)

        filter_grid.addWidget(QLabel("Amount max:"), 2, 2)
        self.filter_amount_max = QDoubleSpinBox()
        self.filter_amount_max.setRange(0, 999_999_999)
        self.filter_amount_max.setDecimals(2)
        self.filter_amount_max.setValue(999_999_999)
        self.filter_amount_max.valueChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_amount_max, 2, 3)

        filter_grid.addWidget(QLabel("Date from:"), 2, 4)
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDate(QDate(1900, 1, 1))
        self.filter_date_from.dateChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_date_from, 2, 5)

        self.btn_clear = QPushButton("Clear Filters")
        self.btn_clear.clicked.connect(self._clear_filters)
        filter_grid.addWidget(self.btn_clear, 3, 0, 1, 2)

        filter_grid.addWidget(QLabel("Date to:"), 3, 4)
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDate(QDate(2100, 12, 31))
        self.filter_date_to.dateChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_date_to, 3, 5)

        filter_group.setLayout(filter_grid)
        layout.addWidget(filter_group)

        # ── Table ──────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference", "CrdtDbt", "Amount", "Date",
            "Counterparty", "Description", "Category",
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        self.setLayout(layout)

    # ── Data loading ───────────────────────────────────────────────────────

    def load_transactions(self):
        self.backend.load_transactions()
        self._populate_category_dropdown()
        self._apply_filters()

    def _populate_category_dropdown(self):
        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItem("All")
        self.filter_category.addItems(self.backend.get_categories())
        self.filter_category.blockSignals(False)

    # ── Filtering ──────────────────────────────────────────────────────────

    def _build_filters(self) -> dict:
        return {
            "reference":    self.filter_reference.text(),
            "cdt_dbt":      self.filter_cdt_dbt.currentText(),
            "category":     self.filter_category.currentText(),
            "counterparty": self.filter_counterparty.text(),
            "description":  self.filter_description.text(),
            "amount_min":   self.filter_amount_min.value(),
            "amount_max":   self.filter_amount_max.value(),
            "date_from":    self.filter_date_from.date().toString("yyyy-MM-dd"),
            "date_to":      self.filter_date_to.date().toString("yyyy-MM-dd"),
        }

    def _apply_filters(self):
        transactions = self.backend.get_filtered_transactions(self._build_filters())
        self._render_table(transactions)

    def _render_table(self, transactions):
        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference or ""))
            self.table.setItem(row, 1, QTableWidgetItem(t.cdt_dbt or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 3, QTableWidgetItem(t.date or ""))
            self.table.setItem(row, 4, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))
            self.table.setItem(row, 6, QTableWidgetItem(t.category_id or ""))
            # Store the Transaction object on column 0 for retrieval on double-click
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, t)

    # ── Double-click ───────────────────────────────────────────────────────

    def _on_row_double_clicked(self, row: int, _column: int):
        t = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dialog = RemoveCategoryDialog(t, parent=self)
        if dialog.exec() == RemoveCategoryDialog.DialogCode.Accepted:
            self.backend.remove_category(t)
            self.load_transactions()

    # ── Clear filters ──────────────────────────────────────────────────────

    def _clear_filters(self):
        widgets = [
            self.filter_reference, self.filter_cdt_dbt, self.filter_category,
            self.filter_counterparty, self.filter_description,
            self.filter_amount_min, self.filter_amount_max,
            self.filter_date_from, self.filter_date_to,
        ]
        for w in widgets:
            w.blockSignals(True)

        self.filter_reference.clear()
        self.filter_cdt_dbt.setCurrentIndex(0)
        self.filter_category.setCurrentIndex(0)
        self.filter_counterparty.clear()
        self.filter_description.clear()
        self.filter_amount_min.setValue(0)
        self.filter_amount_max.setValue(999_999_999)
        self.filter_date_from.setDate(QDate(1900, 1, 1))
        self.filter_date_to.setDate(QDate(2100, 12, 31))

        for w in widgets:
            w.blockSignals(False)

        self._apply_filters()

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self):
        self.stack.setCurrentIndex(0)