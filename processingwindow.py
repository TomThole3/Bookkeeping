# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QTableWidget,
                              QTableWidgetItem, QComboBox, QHeaderView,
                              QFileDialog, QMessageBox, QDoubleSpinBox)
from processingwindowbackend import ProcessingWindowBackend
from categorydialog import AddCategoryDialog


class ProcessingWindow(QWidget):
    def __init__(self, stack):
        super().__init__()

        self.stack = stack
        self.backend = ProcessingWindowBackend()
        self._pending_splits = {}  # reference -> {total, splits: [(amount, category_id)]}

        self.setWindowTitle("Muntenman Schuifwerk")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Reference", "CrdtDbt", "Amount", "Date", "Origin", "Description", "Category", "Split"
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

    # --- private: table management ---

    def _reset_table(self):
        self._pending_splits = {}
        self.table.setRowCount(0)
        self.table.clearContents()

    def _populate_table(self, transactions, categories):
        for transaction in transactions:
            self._pending_splits[transaction.reference] = {
                "total": float(transaction.amount),
                "splits": [(float(transaction.amount), None)]
            }
            self._insert_row(transaction, categories, split_index=0)

    def _insert_row(self, transaction, categories, split_index):
        row = self._find_last_row_for_reference(transaction.reference) + 1
        self.table.insertRow(row)

        is_first = split_index == 0
        if is_first:
            self._set_readonly_item(row, 0, transaction.reference)
            self._set_readonly_item(row, 1, transaction.cdt_dbt)
            self._set_readonly_item(row, 3, transaction.date)
            self._set_readonly_item(row, 4, transaction.origin_name or "")
            self.table.setItem(row, 5, QTableWidgetItem(transaction.description or ""))
        else:
            for col in [0, 1, 3, 4, 5]:
                self._set_readonly_item(row, col, "")

        amount = self._pending_splits[transaction.reference]["splits"][split_index][0]
        self.table.setCellWidget(row, 2, self._create_amount_spinbox(transaction.reference, split_index, amount))
        self.table.setCellWidget(row, 6, self._create_category_combobox(transaction.reference, split_index, categories))

        btn_split = QPushButton("Split")
        btn_split.clicked.connect(
            lambda _, ref=transaction.reference, t=transaction, cats=categories:
            self._split_row(ref, t, cats)
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
        spin.valueChanged.connect(
            lambda value, ref=reference, idx=split_index:
            self._update_split_amount(ref, idx, value)
        )
        return spin

    def _create_category_combobox(self, reference, split_index, categories):
        combo = QComboBox()
        combo.blockSignals(True)
        combo.addItem("", None)
        for cat in categories:
            combo.addItem(cat.name, cat.id)
        combo.blockSignals(False)
        combo.currentIndexChanged.connect(
            lambda _, ref=reference, idx=split_index:
            self._update_split_category(ref, idx, combo.currentData())
        )
        return combo

    # --- private: split state management ---

    def _split_row(self, reference, transaction, categories):
        splits = self._pending_splits[reference]["splits"]
        if len(splits) == 1:
            first_row = self._find_first_row_for_reference(reference)
            self.table.cellWidget(first_row, 2).setReadOnly(False)
        splits.append((0.0, None))
        self._insert_row(transaction, categories, split_index=len(splits) - 1)

    def _find_first_row_for_reference(self, reference):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == reference:
                return row

    def _update_split_amount(self, reference, split_index, value):
        splits = self._pending_splits[reference]["splits"]
        _, category_id = splits[split_index]
        splits[split_index] = (value, category_id)

    def _update_split_category(self, reference, split_index, category_id):
        splits = self._pending_splits[reference]["splits"]
        amount, _ = splits[split_index]
        splits[split_index] = (amount, category_id)

    # --- private: validation ---

    def _validate_splits(self):
        errors = []
        for reference, data in self._pending_splits.items():
            if len(data["splits"]) == 1:
                continue  # unsplit transactions don't need validation
            total = data["total"]
            split_sum = sum(amount for amount, _ in data["splits"])
            if round(split_sum, 2) != round(total, 2):
                errors.append(f"{reference}: amounts sum to {split_sum:.2f}, expected {total:.2f}")
        return errors

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
        errors = self._validate_splits()
        if errors:
            QMessageBox.warning(self, "Split amounts do not add up", "\n".join(errors))
            return

        transactions = []
        for reference, data in self._pending_splits.items():
            description = self._get_description_for_reference(reference)
            for amount, category_id in data["splits"]:
                if category_id is not None:
                    transactions.append((reference, description, category_id, amount, len(data["splits"]) > 1))
        self.backend.save_categories(transactions)
        self.load_transactions()

    def _get_description_for_reference(self, reference):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == reference:
                return self.table.item(row, 5).text()
        return ""

    def _main_screen(self):
        self.stack.setCurrentIndex(0)