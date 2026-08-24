# -*- coding: utf-8 -*-
"""Journal screen for the Muntenman bookkeeping application.

This module defines :class:`JournalWindow`, a filterable table view of
all booked transactions, with the ability to unbook (remove the
category from) a transaction on double-click.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit, QLabel, QHeaderView,
    QStackedWidget,
)
from PyQt6.QtCore import QDate, Qt
from journalwindowbackend import JournalWindowBackend
from unbookdialog import UnbookDialog
from enumerations import Screen

if TYPE_CHECKING:
    # Only needed for type-checking; avoids hard runtime dependencies/
    # circular imports on the concrete database and transaction classes.
    from database import DatabaseInteractions
    from transaction import Transaction


class JournalWindow(QWidget):
    """Screen showing a filterable table of all booked transactions.

    The top bar exposes filters for reference, side, category,
    counterparty, description, amount range, and date range, all of
    which apply live as the user edits them. Double-clicking a
    transaction row opens :class:`UnbookDialog` to confirm removing its
    category.

    Attributes:
        backend: Backend object that loads transactions, applies
            filters, and performs unbook operations.
        stack: The QStackedWidget that manages screen navigation.
        filter_reference: Free-text filter on the reference field.
        filter_side: Dropdown filter on credit/debit side.
        filter_category: Dropdown filter on category.
        filter_counterparty: Free-text filter on counterparty name.
        filter_description: Free-text filter on description.
        filter_amount_min: Minimum-amount filter.
        filter_amount_max: Maximum-amount filter.
        filter_date_from: Start-of-range date filter.
        filter_date_to: End-of-range date filter.
        btn_clear: Button that resets all filters to their defaults.
        table: The table widget displaying filtered transactions.
        btn_return: Button that returns the user to the main menu.
    """

    def __init__(self, stack: QStackedWidget, db: "DatabaseInteractions") -> None:
        """Initialise the journal window.

        Args:
            stack: The QStackedWidget used for screen navigation.
            db: Database interactions object, passed through to the
                backend.
        """
        super().__init__()
        self.backend: JournalWindowBackend = JournalWindowBackend(db)
        self.stack: QStackedWidget = stack
        self._category_map: Dict[int, str] = {}

        self.setWindowTitle("Muntenman Journaal")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()
        
        self.add_filters(layout)
        self.add_table(layout)

        self.btn_return: QPushButton = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

        self.setLayout(layout)

    def add_filters(self, layout: QVBoxLayout) -> None:
        """Build and add the filter panel (grid of filter widgets).

        Every filter widget is wired to :meth:`_apply_filters` so the
        table refreshes live as filters change.

        Args:
            layout: The parent layout to which the filter panel is
                added.
        """
        filter_group = QGroupBox("Filters")
        filter_grid = QGridLayout()
        filter_grid.setHorizontalSpacing(12)
        filter_grid.setVerticalSpacing(6)

        filter_grid.addWidget(QLabel("Reference:"), 0, 0)
        self.filter_reference: QLineEdit = QLineEdit()
        self.filter_reference.setPlaceholderText("Search…")
        self.filter_reference.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_reference, 0, 1)

        filter_grid.addWidget(QLabel("Side:"), 0, 2)
        self.filter_side: QComboBox = QComboBox()
        self.filter_side.addItems(["All", "CRDT", "DBIT"])
        self.filter_side.currentIndexChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_side, 0, 3)

        filter_grid.addWidget(QLabel("Category:"), 0, 4)
        self.filter_category: QComboBox = QComboBox()
        self.filter_category.addItem("All", None)
        self.filter_category.currentIndexChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_category, 0, 5)

        filter_grid.addWidget(QLabel("Counterparty:"), 1, 0)
        self.filter_counterparty: QLineEdit = QLineEdit()
        self.filter_counterparty.setPlaceholderText("Search…")
        self.filter_counterparty.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_counterparty, 1, 1)

        filter_grid.addWidget(QLabel("Description:"), 2, 0)
        self.filter_description: QLineEdit = QLineEdit()
        self.filter_description.setPlaceholderText("Search…")
        self.filter_description.textChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_description, 2, 1)

        self.btn_clear: QPushButton = QPushButton("Clear Filters")
        self.btn_clear.clicked.connect(self._clear_filters)
        filter_grid.addWidget(self.btn_clear, 3, 0, 1, 2)

        filter_grid.addWidget(QLabel("Amount min:"), 1, 2)
        self.filter_amount_min: QDoubleSpinBox = QDoubleSpinBox()
        self.filter_amount_min.setRange(0, 999_999_999)
        self.filter_amount_min.setDecimals(2)
        self.filter_amount_min.setValue(0)
        self.filter_amount_min.valueChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_amount_min, 1, 3)

        filter_grid.addWidget(QLabel("Date from:"), 1, 4)
        self.filter_date_from: QDateEdit = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDate(QDate(1900, 1, 1))
        self.filter_date_from.dateChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_date_from, 1, 5)

        filter_grid.addWidget(QLabel("Amount max:"), 2, 2)
        self.filter_amount_max: QDoubleSpinBox = QDoubleSpinBox()
        self.filter_amount_max.setRange(0, 999_999_999)
        self.filter_amount_max.setDecimals(2)
        self.filter_amount_max.setValue(999_999_999)
        self.filter_amount_max.valueChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_amount_max, 2, 3)

        filter_grid.addWidget(QLabel("Date to:"), 2, 4)
        self.filter_date_to: QDateEdit = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDate(QDate(2100, 12, 31))
        self.filter_date_to.dateChanged.connect(self._apply_filters)
        filter_grid.addWidget(self.filter_date_to, 2, 5)

        filter_group.setLayout(filter_grid)
        layout.addWidget(filter_group)

    def add_table(self, layout: QVBoxLayout) -> None:
        """Build and add the transaction table widget.

        Args:
            layout: The parent layout to which the table is added.
        """
        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference", "Side", "Amount", "Date",
            "Counterparty", "Description", "Category",
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

    # ── Data loading ───────────────────────────────────────────────────────

    def load_transactions(self) -> None:
        """Reload transactions and categories, then reapply filters.

        Fetches fresh data from the backend, rebuilds the category
        filter dropdown, and re-renders the table using the current
        filter values. Called whenever this screen becomes active or
        after a mutation (e.g. an unbook operation).
        """
        self.backend.load_transactions()
        self._category_map = self.backend.get_category_map()
        self._populate_category_dropdown()
        self._apply_filters()

    def _populate_category_dropdown(self) -> None:
        """Rebuild the category filter dropdown from ``_category_map``.

        Signals are blocked during the rebuild so repopulating the
        dropdown doesn't itself trigger a redundant filter refresh.
        """
        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItem("All", None)
        for category_id, name in sorted(self._category_map.items(), key=lambda x: x[1]):
            self.filter_category.addItem(name, category_id)
        self.filter_category.blockSignals(False)

    # ── Filtering ──────────────────────────────────────────────────────────

    def _build_filters(self) -> Dict[str, Any]:
        """Collect the current values of all filter widgets.

        Returns:
            A dict of filter values keyed as expected by
            :meth:`JournalWindowBackend.get_filtered_transactions`:
            ``reference``, ``side``, ``category_id`` (int or ``None``),
            ``counterparty``, ``description``, ``amount_min``,
            ``amount_max``, ``date_from``, and ``date_to``.
        """
        return {
            "reference":    self.filter_reference.text(),
            "side":      self.filter_side.currentText(),
            "category_id":  self.filter_category.currentData(),  # int or None
            "counterparty": self.filter_counterparty.text(),
            "description":  self.filter_description.text(),
            "amount_min":   self.filter_amount_min.value(),
            "amount_max":   self.filter_amount_max.value(),
            "date_from":    self.filter_date_from.date().toString("yyyy-MM-dd"),
            "date_to":      self.filter_date_to.date().toString("yyyy-MM-dd"),
        }

    def _apply_filters(self) -> None:
        """Fetch transactions matching the current filters and re-render the table."""
        transactions = self.backend.get_filtered_transactions(self._build_filters())
        self._render_table(transactions)

    def _render_table(self, transactions: List["Transaction"]) -> None:
        """Populate the table widget with the given transactions.

        Args:
            transactions: The transactions to render, one per row. Each
                row's reference cell also stores the corresponding
                ``Transaction`` object for later retrieval on
                double-click.
        """
        self.table.setRowCount(len(transactions))

        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference or ""))
            self.table.setItem(row, 1, QTableWidgetItem(t.side or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 3, QTableWidgetItem(t.date or ""))
            self.table.setItem(row, 4, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))
            self.table.setItem(row, 6, QTableWidgetItem(
                self._category_map.get(t.category_id, "")
            ))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, t)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 180)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

    # ── Double-click ───────────────────────────────────────────────────────

    def unbook_transaction(self, transaction: "Transaction") -> None:
        """Unbook (remove the category from) a transaction via the backend.

        Args:
            transaction: The transaction to unbook.
        """
        self.backend.unbook_transaction(transaction)

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        """Prompt to unbook the double-clicked transaction and reload.

        Opens :class:`UnbookDialog` for the transaction on the given
        row. If the user confirms, unbooks it via the backend and
        reloads the full transaction list.

        Args:
            row: The row index that was double-clicked.
            _column: The column index that was double-clicked (unused).
        """
        t = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        dialog = UnbookDialog(t, parent=self)
        if dialog.exec() == UnbookDialog.DialogCode.Accepted:
            self.backend.unbook_transaction(t)
            self.load_transactions()

    # ── Clear filters ──────────────────────────────────────────────────────

    def _clear_filters(self) -> None:
        """Reset every filter widget to its default value.

        Signals are blocked while resetting so each individual widget
        change doesn't trigger a redundant filter refresh; a single
        refresh is applied at the end via :meth:`_apply_filters`.
        """
        widgets = [
            self.filter_reference, self.filter_side, self.filter_category,
            self.filter_counterparty, self.filter_description,
            self.filter_amount_min, self.filter_amount_max,
            self.filter_date_from, self.filter_date_to,
        ]
        for w in widgets:
            w.blockSignals(True)

        self.filter_reference.clear()
        self.filter_side.setCurrentIndex(0)
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

    def _main_screen(self) -> None:
        """Navigate back to the main menu screen."""
        self.stack.setCurrentIndex(Screen.MENU)