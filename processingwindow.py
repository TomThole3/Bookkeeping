# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QMessageBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView, QFileDialog, QDoubleSpinBox
from processingwindowbackend import ProcessingWindowBackend
from categorydialog import AddCategoryDialog


class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()

        self.stack = stack
        self.backend = ProcessingWindowBackend(self)

        self.setWindowTitle("Muntenman Schuifwerk")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Reference", "CrdtDbt", "Amount", "Date", "counterparty", "Description", "Category", "Split"
        ])
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        layout.addWidget(self.table)

        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self._add_entries)
        layout.addWidget(self.btn_add_entries)

        self.btn_change_categories = QPushButton("Add/Remove Categories")
        self.btn_change_categories.clicked.connect(self._change_categories)
        layout.addWidget(self.btn_change_categories)

        self.btn_save_categories = QPushButton("Save categories")
        self.btn_save_categories.clicked.connect(self._save_categories)
        layout.addWidget(self.btn_save_categories)

        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

        self.setLayout(layout)
        self.load_transactions()

    # --- public ---

    def load_transactions(self):
        self._reset_table()
        transactions = self.backend.get_uncategorized_transactions()
        categories = self.backend.get_categories()
        self._populate_table(transactions, categories)
        
    def show_sum_error(self, validate):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Invalid split sum")
        msg.setText("The sum of the split amounts does not match the original transaction total.")
     
        msg.setInformativeText(f"Difference: {validate:.2f}")
     
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        

    # --- private: table management ---

    def _reset_table(self):
        self.table.setRowCount(0)
        self.table.clearContents()

    def _populate_table(self, transactions, categories):
        for transaction in transactions: 
            self._insert_row(transaction, categories, split_index=0)

    def _insert_row(self, transaction, categories, split_index):
        row = self._find_last_row_for_reference(transaction.reference) + 1
        self.table.insertRow(row)

        is_first = split_index == 0
        if is_first:
            self._set_readonly_item(row, 0, transaction.reference)
            self._set_readonly_item(row, 1, transaction.cdt_dbt)
            self._set_readonly_item(row, 3, transaction.date)
            self._set_readonly_item(row, 4, transaction.counterparty_name or "")
            self.table.setItem(row, 5, QTableWidgetItem(transaction.description or ""))
        else:
            for col in [0, 1, 3, 4, 5]:
                self._set_readonly_item(row, col, "")

        amount = 0 if split_index else transaction.amount
        self.table.setCellWidget(row, 2, self._create_amount_spinbox(transaction.reference, split_index, amount))
        self.table.setCellWidget(row, 6, self._create_category_combobox(transaction.reference, split_index, categories))

        btn_split = QPushButton("Split")
        btn_split.clicked.connect(
            lambda _, t=transaction, cats=categories:
            self._split_row(t, cats)
        )
        self.table.setCellWidget(row, 7, btn_split)

    def _find_last_row_for_reference(self, reference):
        last_row = -1
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == reference:
                last_row = row
        return last_row

    def _set_readonly_item(self, row, col, value):
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _create_amount_spinbox(self, reference, split_index, amount):
        spin = QDoubleSpinBox()
        spin.setMaximum(99999999.99)
        spin.setDecimals(2)
        spin.setValue(amount)
        return spin

    def _create_category_combobox(self, reference, split_index, categories):
        combo = QComboBox()
        combo.blockSignals(True)
        combo.addItem("", None)
        for cat in categories:
            combo.addItem(cat.name, cat.id)
        combo.blockSignals(False)
        return combo

    # --- private: split state management ---

    def _split_row(self, transaction, categories):
        self._insert_row(transaction, categories, split_index=1)

    # --- private: button handlers ---

    def _add_entries(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "CAMT Files (*.xml);;All Files (*)")
        if path:
            self.backend.import_transactions_from_file(path)
            self.load_transactions()

    def _change_categories(self):
        dialog = AddCategoryDialog()
        dialog.exec()
        self.load_transactions()

    def _save_categories(self):
        table_rows = []

        last_reference = ""
        last_cdt_dbt = ""
        last_date = ""
        last_counterparty = ""
        last_description = ""
        
        for row in range(self.table.rowCount()):
            category_widget = self.table.cellWidget(row, 6)
            if category_widget.currentData() is None:
                continue
            reference_item = self.table.item(row, 0)
            cdt_dbt_item = self.table.item(row, 1)
            date_item = self.table.item(row, 3)
            counterparty_item = self.table.item(row, 4)
            description_item = self.table.item(row, 5)
        
            reference = reference_item.text() if reference_item and reference_item.text() else last_reference
            cdt_dbt = cdt_dbt_item.text() if cdt_dbt_item and cdt_dbt_item.text() else last_cdt_dbt
            date = date_item.text() if date_item and date_item.text() else last_date
            counterparty = counterparty_item.text() if counterparty_item and counterparty_item.text() else last_counterparty
            description = description_item.text() if description_item and description_item.text() else last_description
        
            # update memory
            if reference_item and reference_item.text():
                last_reference = reference
            if cdt_dbt_item and cdt_dbt_item.text():
                last_cdt_dbt = cdt_dbt
            if date_item and date_item.text():
                last_date = date
            if counterparty_item and counterparty_item.text():
                last_counterparty = counterparty
            if description_item and description_item.text():
                last_description = description
        
            amount_widget = self.table.cellWidget(row, 2)
        
            amount = amount_widget.value() if amount_widget else 0.0
            category_id = category_widget.currentData()
        
            table_rows.append({
                "reference": reference,
                "cdt_dbt": cdt_dbt,
                "date": date,
                "counterparty": counterparty,
                "description": description,
                "amount": amount,
                "category_id": category_id,
            })
    
        self.backend.save_categories(table_rows)
        self.load_transactions()

    def _main_screen(self):
        self.stack.setCurrentIndex(0)