# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QFileDialog 
from processingwindowbackend import ProcessingWindowBackend
from categorydialog import AddCategoryDialog

class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()
        
        self.stack = stack
        self.backend = ProcessingWindowBackend()
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
        
    def change_categories(self):
        dialog = AddCategoryDialog()
        dialog.exec()
        self.load_transactions()
        
    def load_transactions(self):
        self._reset_table()
        transactions = self.backend.get_uncategorized_transactions()
        categories = self.backend.get_categories()
        self._populate_table(transactions, categories)
    
    def _reset_table(self):
        self.category_selections = {}
        self.table.clearContents()
    
    def _populate_table(self, transactions, categories):
        self.table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self._populate_row(row, t, categories)
    
    def _populate_row(self, row, transaction, categories):
        self._set_readonly_item(row, 0, transaction.reference)
        self._set_readonly_item(row, 1, transaction.cdt_dbt)
        self._set_readonly_item(row, 2, transaction.amount)
        self._set_readonly_item(row, 3, transaction.date)
        self._set_readonly_item(row, 4, transaction.origin_name or "")
        self.table.setItem(row, 5, QTableWidgetItem(transaction.description or ""))
        combo = self._create_category_combobox(transaction.reference, transaction.category, categories)
        self.table.setCellWidget(row, 6, combo)
            
    def _set_readonly_item(self, row, col, value):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)
        
    def _create_category_combobox(self, reference, category, categories):
        combo = QComboBox()
        combo.blockSignals(True)
        combo.addItem("", None)  # second arg is user data (the id)
        for cat in categories:
            combo.addItem(cat.name, cat.id)  # display name, store id as user data
        if category:
            index = combo.findData(category.id)
            if index >= 0:
                combo.setCurrentIndex(index)
        self.category_selections[reference] = category.id if category else None
        combo.blockSignals(False)
        combo.currentIndexChanged.connect(
            lambda index, ref=reference:
            self.category_selections.update({ref: combo.itemData(index)})
        )
        return combo
            
    def save_categories(self):
        transactions = []
        for row in range(self.table.rowCount()):
            reference = self.table.item(row, 0).text()
            description = self.table.item(row, 5).text()
            category = self.category_selections.get(reference)
            transactions.append((reference, description, category))
        self.backend.save_categories(transactions)
        self.load_transactions()
            
    def add_entries(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "CAMT Files (*.xml);;All Files (*)")
        if path:
            self.backend.import_transactions_from_file(path)
            self.load_transactions()