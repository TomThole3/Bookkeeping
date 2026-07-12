# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from balancewindowbackend import BalanceWindowBackend
from removecategorydialog import RemoveCategoryDialog
from enumerations import Screen, TransactionColumns


class BalanceWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.backend = BalanceWindowBackend()
        self.stack = stack

        self.setWindowTitle("Muntenman Balans")
        self.setGeometry(100, 100, 600, 500)

        layout = QVBoxLayout()
        
        self._create_tree(layout)
        self._add_buttons(layout)
        self.setLayout(layout)
        
    def _create_tree(self, layout):
        self.tree = QTreeWidget()
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
        
    def _add_buttons(self, layout):
        btn_row = QHBoxLayout()
        btn_expand = QPushButton("Expand all")
        btn_expand.clicked.connect(self.tree.expandAll)
        btn_collapse = QPushButton("Collapse all")
        btn_collapse.clicked.connect(self.tree.collapseAll)
        btn_row.addWidget(btn_expand)
        btn_row.addWidget(btn_collapse)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

    # ── Data loading ───────────────────────────────────────────────────────

    def load_categories(self):
        roots = self.backend.get_category_tree_with_totals()
        self.tree.clear()
        for root in roots:
            self.tree.addTopLevelItem(self._build_tree_item(root))
        self.tree.expandAll()
       

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_tree_item(self, category) -> QTreeWidgetItem:
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
        return f"€ {amount:,.2f}"

    # ── Drill-down ─────────────────────────────────────────────────────────

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        category_id = item.data(0, Qt.ItemDataRole.UserRole)
        category_name = item.text(0)
        transactions = self.backend.get_transactions_for_category(category_id)

        drill_down = self.stack.findChild(CategoryTransactionsWindow)
        if drill_down is None:
            drill_down = CategoryTransactionsWindow(self.stack, self.backend)
            self.stack.addWidget(drill_down)

        drill_down.load(category_name, category_id, transactions)
        self.stack.setCurrentWidget(drill_down)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self):
        self.stack.setCurrentIndex(Screen.MENU)


class CategoryTransactionsWindow(QWidget):
    # Human-readable header text for each TransactionColumns entry, kept in
    # column order so it can be built directly from the enum.
    _COLUMN_LABELS = {
        TransactionColumns.REFERENCE: "Reference",
        TransactionColumns.CRDTDBT: "CrdtDbt",
        TransactionColumns.AMOUNT: "Amount",
        TransactionColumns.DATE: "Date",
        TransactionColumns.COUNTERPARTY: "Counterparty",
        TransactionColumns.DESCRIPTION: "Description",
    }

    def __init__(self, stack, backend: BalanceWindowBackend):
        super().__init__()
        self.stack = stack
        self.backend = backend
        self._current_category_id = None

        layout = QVBoxLayout()

        header_row = QHBoxLayout()
        self.btn_back = QPushButton("← Back to balance")
        self.btn_back.clicked.connect(self._go_back)
        header_row.addWidget(self.btn_back)

        self.label_category = QLabel()
        self.label_category.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.label_category.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.label_category.setFont(font)
        header_row.addWidget(self.label_category, stretch=1)

        layout.addLayout(header_row)

        self.table = QTableWidget()
        self.table.setColumnCount(len(TransactionColumns))
        self.table.setHorizontalHeaderLabels(
            [self._COLUMN_LABELS[col] for col in TransactionColumns]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load(self, category_name: str, category_id: int, transactions: list):
        self.setWindowTitle(f"Muntenman — {category_name}")
        self.label_category.setText(category_name)
        self._current_category_id = category_id

        self._render_table(transactions)

    def _render_table(self, transactions: list):
        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.table.setItem(row, TransactionColumns.REFERENCE, QTableWidgetItem(t.reference or ""))
            self.table.setItem(row, TransactionColumns.CRDTDBT, QTableWidgetItem(t.cdt_dbt or ""))
            self.table.setItem(row, TransactionColumns.AMOUNT, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, TransactionColumns.DATE, QTableWidgetItem(t.date or ""))
            self.table.setItem(row, TransactionColumns.COUNTERPARTY, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, TransactionColumns.DESCRIPTION, QTableWidgetItem(t.description or ""))
            # Store Transaction object for retrieval on double-click
            self.table.item(row, TransactionColumns.REFERENCE).setData(Qt.ItemDataRole.UserRole, t)

        for col in TransactionColumns:
            self.table.resizeColumnToContents(col)

    # ── Double-click ───────────────────────────────────────────────────────

    def _on_row_double_clicked(self, row: int, _column: int):
        t = self.table.item(row, TransactionColumns.REFERENCE).data(Qt.ItemDataRole.UserRole)
        dialog = RemoveCategoryDialog(t, parent=self)
        if dialog.exec() == RemoveCategoryDialog.DialogCode.Accepted:
            self.backend.remove_transaction(t)
            transactions = self.backend.get_transactions_for_category(
                self._current_category_id
            )
            self._render_table(transactions)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _go_back(self):
        balance_window = self.stack.findChild(BalanceWindow)
        balance_window.load_categories()  # refresh totals after any removals
        self.stack.setCurrentWidget(balance_window)
