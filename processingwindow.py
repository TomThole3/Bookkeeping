# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QPushButton, QMessageBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QProgressDialog, QComboBox, QHeaderView, QDialog, QFileDialog, QDoubleSpinBox
from processingwindowbackend import ProcessingWindowBackend
from categorydialog import AddCategoryDialog
from memorialdialog import MemorialDialog
from enumerations import TransactionColumns

class ProcessingWindow(QWidget):
    def __init__(self, stack, db):
        super().__init__()

        self.stack = stack
        self.backend = ProcessingWindowBackend(self, db)
        self._ai_suggestions = {}  # {reference: category_id}

        self.setWindowTitle("Processing Transactions")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()
        
        self._add_table(layout)
        self._add_buttons(layout)

        self.setLayout(layout)
        self.load_transactions()
        
    def _add_table(self, layout):
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Reference", "Side", "Amount", "Date", "counterparty", "Description", "Category", "Split"
        ])
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        layout.addWidget(self.table)
        self._setup_column_widths()    
        
    def _add_buttons(self, layout):
        self.btn_add_entries = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self._add_entries)
        layout.addWidget(self.btn_add_entries)

        self.btn_change_categories = QPushButton("Add/Remove Categories")
        self.btn_change_categories.clicked.connect(self._change_categories)
        layout.addWidget(self.btn_change_categories)

        self.btn_book = QPushButton("Book transactions")
        self.btn_book.clicked.connect(self._book)
        layout.addWidget(self.btn_book)
        
        self.btn_auto_categorize = QPushButton("Auto-categorize (AI)")
        self.btn_auto_categorize.clicked.connect(self._auto_categorize)
        layout.addWidget(self.btn_auto_categorize)
        
        self.btn_memorial = QPushButton("New memorialtransaction")
        self.btn_memorial.clicked.connect(self._add_memorial)
        layout.addWidget(self.btn_memorial)
        
        self.btn_return = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)
        
    # --- public ---

    def load_transactions(self):
        self._reset_table()
        transactions = self.backend.get_unbooked_transactions()
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
            self._set_readonly_item(row, 1, transaction.side)
            self._set_readonly_item(row, 3, transaction.date)
            self._set_readonly_item(row, 4, transaction.counterparty_name or "")
            self.table.setItem(row, 5, QTableWidgetItem(transaction.description or ""))
        else:
            for col in [0, 1, 3, 4, 5]:
                self._set_readonly_item(row, col, "")

        amount = 0 if split_index else transaction.amount
        self.table.setCellWidget(row, 2, self._create_amount_spinbox(split_index, amount))
        self.table.setCellWidget(row, 6, self._create_category_combobox(categories))

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

    def _create_amount_spinbox(self, split_index, amount):
        spin = QDoubleSpinBox()
        spin.setMaximum(99999999.99)
        spin.setDecimals(2)
        spin.setValue(amount)
        if split_index == 0:
            spin.setReadOnly(True)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setStyleSheet("QDoubleSpinBox { color: gray; }")
        return spin

    def _create_category_combobox(self, categories):
        combo = QComboBox()
        combo.blockSignals(True)
        combo.addItem("", None)
        for cat in categories:
            combo.addItem(cat.name, cat.id)
        combo.blockSignals(False)
        return combo
    
    def _setup_column_widths(self):
        header = self.table.horizontalHeader()
        # Fixed columns
        self.table.setColumnWidth(TransactionColumns.REFERENCE, 130)  # reference
        self.table.setColumnWidth(TransactionColumns.SIDE, 50)   # side
        self.table.setColumnWidth(TransactionColumns.AMOUNT, 110)  # amount spinbox
        self.table.setColumnWidth(TransactionColumns.DATE, 100)  # date
        self.table.setColumnWidth(TransactionColumns.COUNTERPARTY, 200)  # counterparty
        self.table.setColumnWidth(TransactionColumns.CATEGORY, 180)  # category combobox
        self.table.setColumnWidth(TransactionColumns.SPLIT, 100)   # split button
        # Description (col 5) stretches to fill remaining space
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)

    # --- private: split state management ---

    def _split_row(self, transaction, categories):
        # Enable the amount spinbox on the first row for this reference
        first_row = self._find_last_row_for_reference(transaction.reference)
        if first_row >= 0:
            spin = self.table.cellWidget(first_row, 2)
            if spin:
                spin.setReadOnly(False)
                spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
                spin.setStyleSheet("")
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

    def _book(self):
        table_rows = []
    
        last_reference = last_side = last_date = last_counterparty = last_description = ""
    
        for row in range(self.table.rowCount()):
            category_widget = self.table.cellWidget(row, 6)
            if category_widget.currentData() is None:
                continue
    
            reference_item = self.table.item(row, 0)
            is_continuation = not (reference_item and reference_item.text())
    
            if is_continuation:
                reference    = last_reference
                side      = last_side
                date         = last_date
                counterparty = last_counterparty
                description  = last_description
            else:
                reference    = reference_item.text()
                side      = self.table.item(row, 1).text()
                date         = self.table.item(row, 3).text()
                counterparty = self.table.item(row, 4).text()
                description  = self.table.item(row, 5).text()
    
                last_reference, last_side, last_date, last_counterparty, last_description = (
                    reference, side, date, counterparty, description
                )
    
            amount_widget = self.table.cellWidget(row, 2)
            amount = amount_widget.value() if amount_widget else 0.0
            category_id = category_widget.currentData()
    
            table_rows.append({
                "reference": reference,
                "side": side,
                "date": date,
                "counterparty": counterparty,
                "description": description,
                "amount": amount,
                "category_id": category_id,
            })
    
        for row_data in table_rows:
           reference = row_data["reference"]
           actual_category_id = row_data["category_id"]
           ai_suggested_id = self._ai_suggestions.get(reference)
    
           # Save as example if:
           # - AI made a suggestion but user changed it (correction)
           # - AI made no suggestion but user categorized it anyway (new example)
           is_split = self._is_split_reference(reference)
           if not is_split and ai_suggested_id != actual_category_id and actual_category_id != '':
               self.backend.save_categorization_example(
                   counterparty=row_data["counterparty"],
                   description=row_data["description"],
                   amount=row_data["amount"],
                   side=row_data["side"],
                   category_id=actual_category_id,
               )
    
        self.backend.book_transactions(table_rows)
        self._ai_suggestions = {}  # reset after save
        self.load_transactions()
        
        # a i 
        
    def _auto_categorize(self):
        transactions = self.backend.get_unbooked_transactions()
        categories = self.backend.get_categories()
    
        if not transactions:
            QMessageBox.information(self, "Nothing to do", "No unbooked transactions.")
            return
    
        progress = QProgressDialog("Asking Phi-4 Mini...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
    
        try:
            assignments = self.backend.get_ai_suggestions(transactions, categories)
        except Exception as e:
            QMessageBox.critical(self, "AI Error", f"Categorization failed:\n{e}")
            return
        finally:
            progress.close()
    
        self._apply_suggestions(assignments)
        QMessageBox.information(
            self, "Done",
            f"AI suggested categories for {len(assignments)} transaction(s). Review and save."
        )
        
    def _apply_suggestions(self, assignments: dict):
        self._ai_suggestions = assignments
        for row in range(self.table.rowCount()):
            ref_item = self.table.item(row, 0)
            if not ref_item or not ref_item.text():
                continue
            reference = ref_item.text()
            if reference not in assignments:
                continue
            combo = self.table.cellWidget(row, 6)
            if combo is None:
                continue
            category_id = assignments[reference]
            for i in range(combo.count()):
                if combo.itemData(i) == category_id:
                    combo.setCurrentIndex(i)
                    break
            
    def _is_split_reference(self, reference: str) -> bool:
        count = sum(
            1 for row in range(self.table.rowCount())
            if self.table.item(row, 0) and self.table.item(row, 0).text() == reference
        )
        return count > 1
    
    def _add_memorial(self):
        categories = self.backend.get_categories()
        if not categories:
            QMessageBox.warning(self, "Error", "No categories exist")
            return
        dialog = MemorialDialog(categories, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()
            self.backend.save_memorial_transaction(
                date=values["date"],
                description=values["description"],
                amount=values["amount"],
                from_category_id=values["from_category_id"],
                to_category_id=values["to_category_id"],
            )
            QMessageBox.information(self, "Succes", "Memorialtransaction is saved.")

    def _main_screen(self):
        self.stack.setCurrentIndex(0)