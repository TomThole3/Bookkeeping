# -*- coding: utf-8 -*-
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem
from processingwindowbackend import ProcessingWindowBackend

class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        
        self.stack = stack
        self.backend = ProcessingWindowBackend(self.stack)
        
        self.setWindowTitle("Muntenman Schuifwerk")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Reference",
            "Amount",
            "Date",
            "Origin",
            "Description",
            "Category"
        ])
        
        layout.addWidget(self.table)

        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_entries)
        
        self.setLayout(layout)

    def add_entries(self):
        self.backend.add_entries()
        
    def load_transactions(self):
        transactions = self.backend.get_all_transactions()
        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.table.setItem(row, 0, QTableWidgetItem(t.reference))
            self.table.setItem(row, 1, QTableWidgetItem(str(t.amount)))
            self.table.setItem(row, 2, QTableWidgetItem(t.date))
            self.table.setItem(row, 3, QTableWidgetItem(t.origin))
            self.table.setItem(row, 4, QTableWidgetItem(t.description or ""))
            self.table.setItem(row, 5, QTableWidgetItem(t.category or ""))
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProcessingWindow()
    window.show()
    sys.exit(app.exec())