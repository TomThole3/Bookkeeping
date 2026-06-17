# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from journalwindowbackend import JournalWindowBackend

class JournalWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.backend = JournalWindowBackend()

        self.setWindowTitle("Muntenman Journaal")
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference",
            "CrdtDbt",
            "Amount",
            "Date",
            "Origin",
            "Description",
            "Category"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_transactions()

    def load_transactions(self):
        transactions = self.backend.get_categorized_transactions()
        self.table.setRowCount(len(transactions))

        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference))
            self.table.setItem(row, 1, QTableWidgetItem(t.cdt_dbt))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 3, QTableWidgetItem(t.date))
            self.table.setItem(row, 4, QTableWidgetItem(t.origin_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))
            self.table.setItem(row, 6, QTableWidgetItem(t.category_id or ""))