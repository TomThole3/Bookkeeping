# -*- coding: utf-8 -*-
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox
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
        
        layout.addWidget(self.table)
        self.load_transactions()

        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_entries)
        
        self.btn_change_categories = QPushButton("Add/Remove Categories")
        self.btn_change_categories.clicked.connect(self.change_categories)
        layout.addWidget(self.btn_change_categories)
        
        self.setLayout(layout)

    def add_entries(self):
        self.backend.add_entries()
        
    def change_categories(self):
        self.backend.change_categories()
        self.load_transactions()
        
    def load_transactions(self):
    
        transactions = self.backend.get_all_transactions()
        self.table.setRowCount(len(transactions))
    
        categories = self.backend.get_categories()
    
        for row, t in enumerate(transactions):
    
            # 0. Reference (READ ONLY)
            item = QTableWidgetItem(t.reference)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, item)
    
            # 1. C/D (READ ONLY)
            item = QTableWidgetItem(t.cdt_dbt)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, item)
    
            # 2. Amount (READ ONLY)
            item = QTableWidgetItem(str(t.amount))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, item)
    
            # 3. Date (READ ONLY)
            item = QTableWidgetItem(t.date)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 3, item)
    
            # 4. Origin name (READ ONLY)
            item = QTableWidgetItem(t.origin_name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item)
    
            # 5. Description (EDITABLE)
            self.table.setItem(
                row,
                5,
                QTableWidgetItem(t.description or "")
            )
    
            # 6. CATEGORY (DROPDOWN)
            combo = QComboBox()
            combo.addItem('')
            combo.addItems(categories)
            
            
    
            # set current value if it exists
            if t.category and t.category in categories:
                combo.setCurrentText(t.category)
            else:
                combo.setCurrentText("Uncategorized")
    
            self.table.setCellWidget(row, 6, combo)
