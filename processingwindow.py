# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView 
from processingwindowbackend import ProcessingWindowBackend

class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        
        self.stack = stack
        self.backend = ProcessingWindowBackend(self.stack)
        self.category_selections = {}  # reference -> category
        
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
        
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        
        layout.addWidget(self.table)
        self.load_transactions()

        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self.add_entries)
        layout.addWidget(self.btn_add_entries)
        
        self.btn_change_categories = QPushButton("Add/Remove Categories")
        self.btn_change_categories.clicked.connect(self.change_categories)
        layout.addWidget(self.btn_change_categories)
        
        self.btn_save_categories = QPushButton("Save categories")
        self.btn_save_categories.clicked.connect(self.save_categories)
        layout.addWidget(self.btn_save_categories)

        self.setLayout(layout)

    def add_entries(self):
        self.backend.add_entries()
        
    def change_categories(self):
        self.backend.change_categories()
        self.load_transactions()
        
    def load_transactions(self):
        self.category_selections = {}  # reset on reload
        self.table.clearContents()  # clears all cell widgets and items
        
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
            item = QTableWidgetItem(t.origin_name or "")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, item)
    
            # 5. Description (EDITABLE)
            self.table.setItem(row, 5, QTableWidgetItem(t.description or ""))
    
            # 6. CATEGORY (DROPDOWN)
            combo = QComboBox()
            combo.blockSignals(True)  # don't fire signals while building
            combo.addItem('')
            combo.addItems(categories)
            
            if t.category and t.category in categories:
                combo.setCurrentText(t.category)
                self.category_selections[t.reference] = t.category
            else:
                self.category_selections[t.reference] = None
            
            combo.blockSignals(False)  # re-enable signals before connecting
            
            combo.currentTextChanged.connect(
                lambda text, ref=t.reference: self.category_selections.update({ref: text or None})
            )
            
            self.table.setCellWidget(row, 6, combo)
            
    def save_categories(self):
        transactions = []

        for row in range(self.table.rowCount()):
            reference_item = self.table.item(row, 0)
            description_item = self.table.item(row, 5)
            if reference_item is None:
                continue

            reference = reference_item.text()
            description = description_item.text() if description_item else ""
            category = self.category_selections.get(reference, None)

            transactions.append((reference, description, category))

        self.backend.save_categories(transactions)
        self.load_transactions()