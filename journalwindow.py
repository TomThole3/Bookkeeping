# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from journalwindowbackend import JournalWindowBackend

class JournalWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.backend = JournalWindowBackend()
        self.stack = stack

        self.setWindowTitle("Muntenman Journaal")
        self.setGeometry(100, 100, 800, 600)
        layout = QVBoxLayout()

        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Reference",
            "CrdtDbt",
            "Amount",
            "Date",
            "counterparty",
            "Description",
            "Category"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_transactions(self):
        transactions = self.backend.get_categorized_transactions()
        self.table.setRowCount(len(transactions))

        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference))
            self.table.setItem(row, 1, QTableWidgetItem(t.cdt_dbt))
            self.table.setItem(row, 2, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 3, QTableWidgetItem(t.date))
            self.table.setItem(row, 4, QTableWidgetItem(t.counterparty_name or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))
            self.table.setItem(row, 6, QTableWidgetItem(t.category_id or ""))
            
    def _main_screen(self):
        self.stack.setCurrentIndex(0)