# -*- coding: utf-8 -*-
"""Balance screen for the bookkeeping application.

This module defines two widgets:

* :class:`BalanceWindow` — shows a category tree with rolled-up income,
  expenditure, and net totals for every category (including descendants).
* :class:`CategoryTransactionsWindow` — a drill-down screen showing the
  individual transactions booked directly under a single category,
  reached by double-clicking a row in the tree.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView,
    QStackedWidget,
)
from PyQt6.QtCore import Qt
from balancewindowbackend import BalanceWindowBackend
from unbookdialog import UnbookDialog
from enumerations import Screen, BalanceColumns

if TYPE_CHECKING:
    # Only needed for type-checking; avoids hard runtime dependencies/
    # circular imports on the concrete database, category, and
    # transaction classes.
    from database import DatabaseInteractions
    from category import Category
    from transaction import Transaction


class BalanceWindow(QWidget):
    """Screen showing a category tree with rolled-up financial totals.

    Each row displays a category's name along with its income,
    expenditure, and net total, aggregated to include all descendant
    categories. Double-clicking a row opens a drill-down screen listing
    the individual transactions booked directly under that category.

    Attributes:
        backend: Backend object that computes the category tree and
            totals, and performs unbook operations.
        stack: The QStackedWidget that manages screen navigation.
        tree: The tree widget displaying categories and their totals.
        btn_return: Button that returns the user to the main menu.
    """

    def __init__(self, stack: QStackedWidget, db: "DatabaseInteractions") -> None:
        """Initialise the balance window.

        Args:
            stack: The QStackedWidget used for screen navigation.
            db: Database interactions object, passed through to the backend.
        """
        super().__init__()
        self.backend: BalanceWindowBackend = BalanceWindowBackend(db)
        self.stack: QStackedWidget = stack

        self.setWindowTitle("Balans")
        self.setGeometry(100, 100, 600, 500)

        layout = QVBoxLayout()
        
        self._create_tree(layout)
        self._add_buttons(layout)
        self.setLayout(layout)

    def _create_tree(self, layout: QVBoxLayout) -> None:
        """Create and configure the category tree widget.

        Args:
            layout: The parent layout to which the tree is added.
        """
        self.tree: QTreeWidget = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Category", "Income", "Expenditure", "Total"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        for col in (1, 2, 3):
            self.tree.headerItem().setTextAlignment(col, Qt.AlignmentFlag.AlignRight)
        header = self.tree.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 130)
        self.tree.setColumnWidth(3, 90)
        layout.addWidget(self.tree)

    def _add_buttons(self, layout: QVBoxLayout) -> None:
        """Create and add the expand/collapse/return button row.

        Args:
            layout: The parent layout to which the button row is added.
        """
        btn_row = QHBoxLayout()
        btn_expand = QPushButton("Expand all")
        btn_expand.clicked.connect(self.tree.expandAll)
        btn_collapse = QPushButton("Collapse all")
        btn_collapse.clicked.connect(self.tree.collapseAll)
        btn_row.addWidget(btn_expand)
        btn_row.addWidget(btn_collapse)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.btn_return: QPushButton = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

    # ── Data loading ───────────────────────────────────────────────────────

    def load_categories(self) -> None:
        """Reload the category tree from the backend and redisplay it.

        Fetches the current category tree (with rolled-up totals) from
        the backend, clears the tree widget, rebuilds it from scratch,
        and expands every node. Called whenever this screen becomes
        active or after a mutation (e.g. an unbook operation) that may
        have changed totals.
        """
        roots = self.backend.get_category_tree_with_totals()
        self.tree.clear()
        for root in roots:
            self.tree.addTopLevelItem(self._build_tree_item(root))
        self.tree.expandAll()
       

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_tree_item(self, category: "Category") -> QTreeWidgetItem:
        """Recursively build a tree item for a category and its children.

        Args:
            category: A category with a ``totals`` attribute (as set by
                :meth:`BalanceWindowBackend.get_category_tree_with_totals`)
                and populated ``children``.

        Returns:
            A :class:`QTreeWidgetItem` displaying the category's name and
            formatted totals, with its ``children`` recursively attached
            as child items.
        """
        totals = category.totals
        item = QTreeWidgetItem([
            category.name,
            self._fmt(totals.income),
            self._fmt(totals.expenditure),
            self._fmt(totals.total),
        ])
        item.setData(0, Qt.ItemDataRole.UserRole, category.id)

        for col in (1, 2, 3):
            item.setTextAlignment(col, Qt.AlignmentFlag.AlignRight)

        for child in category.children:
            item.addChild(self._build_tree_item(child))

        return item

    @staticmethod
    def _fmt(amount: float) -> str:
        """Format an amount as a Euro-denominated string.

        Args:
            amount: The numeric amount to format.

        Returns:
            The amount formatted as e.g. ``"€ 1,234.56"``.
        """
        return f"€ {amount:,.2f}"

    # ── Drill-down ─────────────────────────────────────────────────────────

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Open the drill-down screen for the double-clicked category.

        Lazily creates (and caches on the stack) a single
        :class:`CategoryTransactionsWindow` instance, then loads it with
        the transactions belonging directly to the selected category and
        switches the stack to show it.

        Args:
            item: The tree item that was double-clicked.
            column: The column index that was double-clicked (unused).
        """
        category_id: int = item.data(0, Qt.ItemDataRole.UserRole)
        category_name: str = item.text(0)
        transactions = self.backend.get_transactions_for_category(category_id)

        drill_down = self.stack.findChild(CategoryTransactionsWindow)
        if drill_down is None:
            drill_down = CategoryTransactionsWindow(self.stack, self.backend)
            self.stack.addWidget(drill_down)

        drill_down.load(category_name, category_id, transactions)
        self.stack.setCurrentWidget(drill_down)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self) -> None:
        """Navigate back to the main menu screen."""
        self.stack.setCurrentIndex(Screen.MENU)


class CategoryTransactionsWindow(QWidget):
    """Drill-down screen listing transactions booked under one category.

    Reached by double-clicking a category row in :class:`BalanceWindow`.
    Double-clicking a transaction row opens :class:`UnbookDialog` to
    confirm removing its category (or deleting a memorial pair / split
    group, as applicable).

    Attributes:
        stack: The QStackedWidget that manages screen navigation.
        backend: Backend object shared with :class:`BalanceWindow`, used
            to fetch transactions and perform unbook operations.
        table: The table widget displaying the category's transactions.
        btn_back: Button that navigates back to :class:`BalanceWindow`.
        label_category: Label showing the current category's name.
    """

    # Human-readable header text for each TransactionColumns entry, kept in
    # column order so it can be built directly from the enum.
    _COLUMN_LABELS: Dict[BalanceColumns, str] = {
        BalanceColumns.REFERENCE: "Reference",
        BalanceColumns.SIDE: "Side",
        BalanceColumns.AMOUNT: "Amount",
        BalanceColumns.DATE: "Date",
        BalanceColumns.COUNTERPARTY: "Counterparty",
        BalanceColumns.DESCRIPTION: "Description",
    }

    def __init__(self, stack: QStackedWidget, backend: BalanceWindowBackend) -> None:
        """Initialise the drill-down screen.

        Args:
            stack: The QStackedWidget used for screen navigation.
            backend: The same :class:`BalanceWindowBackend` instance used
                by the parent :class:`BalanceWindow`.
        """
        super().__init__()
        self.stack: QStackedWidget = stack
        self.backend: BalanceWindowBackend = backend
        self._current_category_id: Optional[int] = None

        layout = QVBoxLayout()

        header_row = QHBoxLayout()
        self.btn_back: QPushButton = QPushButton("← Back to balance")
        self.btn_back.clicked.connect(self._go_back)
        header_row.addWidget(self.btn_back)

        self.label_category: QLabel = QLabel()
        self.label_category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.label_category.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.label_category.setFont(font)
        header_row.addWidget(self.label_category, stretch=1)

        layout.addLayout(header_row)

        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(len(BalanceColumns))
        self.table.setHorizontalHeaderLabels(
            [self._COLUMN_LABELS[col] for col in BalanceColumns]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load(self, category_name: str, category_id: int, transactions: List["Transaction"]) -> None:
        """Load and display transactions for a category.

        Args:
            category_name: Display name of the category, shown in the
                window title and header label.
            category_id: ID of the category being drilled into. Cached
                so the table can be refreshed after an unbook operation.
            transactions: The transactions to display, belonging
                directly to this category.
        """
        self.setWindowTitle(f"{category_name}")
        self.label_category.setText(category_name)
        self._current_category_id = category_id

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
            self.table.setItem(row, BalanceColumns.REFERENCE, QTableWidgetItem(t.reference or ""))
            self.table.setItem(row, BalanceColumns.SIDE, QTableWidgetItem(t.side or ""))
            self.table.setItem(row, BalanceColumns.AMOUNT, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, BalanceColumns.DATE, QTableWidgetItem(t.date or ""))
            self.table.setItem(row, BalanceColumns.COUNTERPARTY, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, BalanceColumns.DESCRIPTION, QTableWidgetItem(t.description or ""))
            # Store Transaction object for retrieval on double-click
            self.table.item(row, BalanceColumns.REFERENCE).setData(Qt.ItemDataRole.UserRole, t)

        for col in BalanceColumns:
            self.table.resizeColumnToContents(col)

    # ── Double-click ───────────────────────────────────────────────────────

    def _on_row_double_clicked(self, row: int, _column: int) -> None:
        """Prompt to unbook the double-clicked transaction and refresh.

        Opens :class:`UnbookDialog` for the transaction on the given row.
        If the user confirms, asks the backend to unbook it and
        re-renders the table with the updated set of transactions for
        the current category.

        Args:
            row: The row index that was double-clicked.
            _column: The column index that was double-clicked (unused).
        """
        t = self.table.item(row, BalanceColumns.REFERENCE).data(Qt.ItemDataRole.UserRole)
        dialog = UnbookDialog(t, parent=self)
        if dialog.exec() == UnbookDialog.DialogCode.Accepted:
            self.backend.unbook_transaction(t)
            transactions = self.backend.get_transactions_for_category(
                self._current_category_id
            )
            self._render_table(transactions)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _go_back(self) -> None:
        """Navigate back to :class:`BalanceWindow`, refreshing its totals.

        Totals are refreshed because an unbook operation performed on
        this screen may have changed category income/expenditure sums.
        """
        balance_window = self.stack.findChild(BalanceWindow)
        balance_window.load_categories()  # refresh totals after any removals
        self.stack.setCurrentWidget(balance_window)