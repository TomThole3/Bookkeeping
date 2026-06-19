# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel,
)
from PyQt6.QtCore import Qt
from balancewindowbackend import BalanceWindowBackend


class BalanceWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.backend = BalanceWindowBackend()
        self.stack = stack

        self.setWindowTitle("Muntenman Balans")
        self.setGeometry(100, 100, 600, 500)

        layout = QVBoxLayout()

        # ── Return button ──────────────────────────────────────────────────
        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

        # ── Tree ───────────────────────────────────────────────────────────
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Category", "Income", "Expenditure", "Total"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(False)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        for col in (1, 2, 3):
            self.tree.headerItem().setTextAlignment(col, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.tree)

        # ── Expand / collapse controls ─────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_expand = QPushButton("Expand all")
        btn_expand.clicked.connect(self.tree.expandAll)
        btn_collapse = QPushButton("Collapse all")
        btn_collapse.clicked.connect(self.tree.collapseAll)
        btn_row.addWidget(btn_expand)
        btn_row.addWidget(btn_collapse)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.setLayout(layout)

    # ── Data loading ───────────────────────────────────────────────────────

    def load_categories(self):
        roots = self.backend.get_category_tree_with_totals()
        self.tree.clear()
        for root in roots:
            item = self._build_tree_item(root)
            self.tree.addTopLevelItem(item)
        self.tree.expandAll()
        for col in range(4):
            self.tree.resizeColumnToContents(col)

    # ── Private helpers ────────────────────────────────────────────────────

    def _build_tree_item(self, category) -> QTreeWidgetItem:
        totals = category.totals
        item = QTreeWidgetItem([
            category.name,
            self._fmt(totals.income),
            self._fmt(totals.expenditure),
            self._fmt(totals.total),
        ])
        # Store the integer category id for use in the double-click handler
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

        # Find or create the drill-down screen in the stack
        drill_down = self.stack.findChild(CategoryTransactionsWindow)
        if drill_down is None:
            drill_down = CategoryTransactionsWindow(self.stack)
            self.stack.addWidget(drill_down)

        drill_down.load(category_name, transactions)
        self.stack.setCurrentWidget(drill_down)

    # ── Navigation ─────────────────────────────────────────────────────────

    def _main_screen(self):
        self.stack.setCurrentIndex(0)


class CategoryTransactionsWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.stack = stack

        layout = QVBoxLayout()

        # ── Header row: back button + category label ───────────────────────
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

        # ── Table ──────────────────────────────────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Reference", "CrdtDbt", "Amount", "Date",
            "Counterparty", "Description",
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def load(self, category_name: str, transactions: list):
        self.setWindowTitle(f"Muntenman — {category_name}")
        self.label_category.setText(category_name)

        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference or ""))
            self.table.setItem(row, 1, QTableWidgetItem(t.cdt_dbt or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 3, QTableWidgetItem(t.date or ""))
            self.table.setItem(row, 4, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))

        for col in range(6):
            self.table.resizeColumnToContents(col)

    def _go_back(self):
        self.stack.setCurrentWidget(
            self.stack.findChild(BalanceWindow)
        )