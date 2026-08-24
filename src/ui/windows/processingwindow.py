# -*- coding: utf-8 -*-
"""Processing screen for the bookkeeping application.

This module defines :class:`ProcessingWindow`, the screen used to import
new bank transactions, categorise (manually or via AI) and optionally
split them, and book them into the ledger. It also provides entry
points for managing categories and creating memorial transactions.
"""

from __future__ import annotations

from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QMessageBox, QVBoxLayout, QTableWidget,
    QTableWidgetItem, QProgressDialog, QComboBox, QHeaderView, QDialog,
    QFileDialog, QDoubleSpinBox, QStackedWidget,
)
from ui.backends.processingwindowbackend import ProcessingWindowBackend
from ui.dialogs.categorydialog import AddCategoryDialog
from ui.dialogs.memorialdialog import MemorialDialog
from util.enumerations import TransactionColumns

from data.database import DatabaseInteractions
from models.category import Category
from models.transaction import Transaction

# A single row of booking data collected from the table before being
# handed to the backend's book_transactions().
BookingRow = Dict[str, Any]


class ProcessingWindow(QWidget):
    """Screen for importing, categorising, splitting, and booking transactions.

    Unbooked transactions are shown one row per transaction (or per
    split part, once split). Each row lets the user pick a category via
    a combo box; a transaction can be divided into multiple parts using
    the "Split" button, each part getting its own amount and category.
    "Book transactions" persists every row with a selected category,
    validating that split amounts sum back to the original total.

    Attributes:
        stack: The QStackedWidget that manages screen navigation.
        backend: Backend object handling imports, categorisation,
            booking, and memorial transactions.
        table: The table widget listing unbooked transactions (and
            their split parts).
        btn_add_entries: Button that imports a new CAMT file.
        btn_change_categories: Button that opens the category management
            dialog.
        btn_book: Button that books all categorised rows.
        btn_auto_categorize: Button that requests AI category
            suggestions for all unbooked transactions.
        btn_memorial: Button that opens the memorial transaction dialog.
        btn_return: Button that returns the user to the main menu.
    """

    def __init__(self, stack: QStackedWidget, db: "DatabaseInteractions") -> None:
        """Initialise the processing window and load unbooked transactions.

        Args:
            stack: The QStackedWidget used for screen navigation.
            db: Database interactions object, passed through to the
                backend.
        """
        super().__init__()

        self.stack: QStackedWidget = stack
        self.backend: ProcessingWindowBackend = ProcessingWindowBackend(self, db)
        self._ai_suggestions: Dict[str, int] = {}  # {reference: category_id}

        self.setWindowTitle("Processing Transactions")
        self.setGeometry(100, 100, 300, 200)

        layout = QVBoxLayout()
        
        self._add_table(layout)
        self._add_buttons(layout)

        self.setLayout(layout)
        self.load_transactions()

    def _add_table(self, layout: QVBoxLayout) -> None:
        """Create and configure the unbooked-transactions table.

        Args:
            layout: The parent layout to which the table is added.
        """
        self.table: QTableWidget = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Reference", "Side", "Amount", "Date", "counterparty", "Description", "Category", "Split"
        ])
        self.table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        layout.addWidget(self.table)
        self._setup_column_widths()

    def _add_buttons(self, layout: QVBoxLayout) -> None:
        """Create and add the action button column.

        Args:
            layout: The parent layout to which the buttons are added.
        """
        self.btn_add_entries: QPushButton = QPushButton("Add new entries")
        self.btn_add_entries.clicked.connect(self._add_entries)
        layout.addWidget(self.btn_add_entries)

        self.btn_change_categories: QPushButton = QPushButton("Add/Remove Categories")
        self.btn_change_categories.clicked.connect(self._change_categories)
        layout.addWidget(self.btn_change_categories)

        self.btn_book: QPushButton = QPushButton("Book transactions")
        self.btn_book.clicked.connect(self._book)
        layout.addWidget(self.btn_book)
        
        self.btn_auto_categorize: QPushButton = QPushButton("Auto-categorize (AI)")
        self.btn_auto_categorize.clicked.connect(self._auto_categorize)
        layout.addWidget(self.btn_auto_categorize)
        
        self.btn_memorial: QPushButton = QPushButton("New memorialtransaction")
        self.btn_memorial.clicked.connect(self._add_memorial)
        layout.addWidget(self.btn_memorial)
        
        self.btn_return: QPushButton = QPushButton("Return to mainscreen")
        self.btn_return.clicked.connect(self._main_screen)
        layout.addWidget(self.btn_return)

    # --- public ---

    def load_transactions(self) -> None:
        """Reload unbooked transactions and categories, then repopulate the table.

        Clears the table and rebuilds it from scratch based on the
        current unbooked transactions and available categories. Called
        on init and after any operation that changes the set of
        unbooked transactions (import, booking, category changes).
        """
        self._reset_table()
        transactions = self.backend.get_unbooked_transactions()
        categories = self.backend.get_categories()
        self._populate_table(transactions, categories)

    def show_sum_error(self, validate: float) -> None:
        """Show a warning dialog reporting a split-amount mismatch.

        Args:
            validate: The difference between the sum of split amounts
                and the original transaction total (as computed by the
                backend). Displayed to the user for troubleshooting.
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Invalid split sum")
        msg.setText("The sum of the split amounts does not match the original transaction total.")
     
        msg.setInformativeText(f"Difference: {validate:.2f}")
     
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

    # --- private: table management ---

    def _reset_table(self) -> None:
        """Remove all rows and cell widgets from the table."""
        self.table.setRowCount(0)
        self.table.clearContents()

    def _populate_table(
        self, transactions: List["Transaction"], categories: List["Category"]
    ) -> None:
        """Insert one initial row per unbooked transaction.

        Args:
            transactions: The unbooked transactions to display.
            categories: Available categories, used to populate each
                row's category combo box.
        """
        for transaction in transactions: 
            self._insert_row(transaction, categories, split_index=0)

    def _insert_row(
        self, transaction: "Transaction", categories: List["Category"], split_index: int
    ) -> None:
        """Insert a single table row for a transaction or one of its split parts.

        The row is appended directly after any existing rows for the
        same transaction reference. The first row (``split_index == 0``)
        shows the transaction's reference, side, date, counterparty, and
        description, with a read-only amount pre-filled from the
        transaction; subsequent split rows leave those columns blank and
        start with an editable amount of ``0``.

        Args:
            transaction: The transaction this row represents (or is a
                split part of).
            categories: Available categories, used to populate the
                row's category combo box.
            split_index: ``0`` for the transaction's original (first)
                row, or ``>= 1`` for an additional split part.
        """
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

    def _find_last_row_for_reference(self, reference: str) -> int:
        """Find the last table row belonging to a given transaction reference.

        Args:
            reference: The transaction reference to search for.

        Returns:
            The index of the last row whose reference cell matches
            ``reference``, or ``-1`` if no such row exists.
        """
        last_row = -1
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == reference:
                last_row = row
        return last_row

    def _set_readonly_item(self, row: int, col: int, value: Any) -> None:
        """Set a table cell to a non-editable text item.

        Args:
            row: Row index of the cell.
            col: Column index of the cell.
            value: Value to display; converted to ``str``.
        """
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, col, item)

    def _create_amount_spinbox(self, split_index: int, amount: float) -> QDoubleSpinBox:
        """Create the amount spin box widget for a table row.

        The spin box for a transaction's first (non-split) row is
        read-only and greyed out, since its amount is fixed to the
        original transaction total unless the row is split. Rows added
        via splitting get an editable spin box.

        Args:
            split_index: ``0`` for the original row (produces a
                read-only spin box), ``>= 1`` for a split part
                (produces an editable spin box).
            amount: Initial value for the spin box.

        Returns:
            A configured :class:`QDoubleSpinBox`.
        """
        spin = QDoubleSpinBox()
        spin.setMaximum(99999999.99)
        spin.setDecimals(2)
        spin.setValue(amount)
        if split_index == 0:
            spin.setReadOnly(True)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setStyleSheet("QDoubleSpinBox { color: gray; }")
        return spin

    def _create_category_combobox(self, categories: List["Category"]) -> QComboBox:
        """Create a category selection combo box for a table row.

        Args:
            categories: Categories to populate the combo box with. A
                blank ``("", None)`` entry is prepended, representing
                "no category selected".

        Returns:
            A configured :class:`QComboBox`.
        """
        combo = QComboBox()
        combo.blockSignals(True)
        combo.addItem("", None)
        for cat in categories:
            combo.addItem(cat.name, cat.id)
        combo.blockSignals(False)
        return combo

    def _setup_column_widths(self) -> None:
        """Set fixed widths for all columns except Description, which stretches."""
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

    def _split_row(self, transaction: "Transaction", categories: List["Category"]) -> None:
        """Enable editing of the original row's amount and add a new split row.

        Args:
            transaction: The transaction being split.
            categories: Available categories, passed through to the new
                row's category combo box.
        """
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

    def _add_entries(self) -> None:
        """Prompt for a CAMT file, import it, and reload the table.

        Does nothing if the user cancels the file dialog.
        """
        path, _ = QFileDialog.getOpenFileName(self, "Select a file", "", "CAMT Files (*.xml);;All Files (*)")
        if path:
            self.backend.import_transactions_from_file(path)
            self.load_transactions()

    def _change_categories(self) -> None:
        """Open the category management dialog and reload the table afterward."""
        dialog = AddCategoryDialog()
        dialog.exec()
        self.load_transactions()

    def _book(self) -> None:
        """Book every table row that has a category selected.

        Walks the table collecting one :data:`BookingRow` per row with
        a non-empty category selection (continuation rows for split
        transactions inherit reference/side/date/counterparty/
        description from the transaction's first row). For each row
        whose actual category differs from any AI suggestion made for
        it (or that had no AI suggestion at all), saves it as a new
        few-shot categorisation example — unless the transaction was
        split, since a partial amount isn't representative. Finally
        hands all collected rows to the backend to persist, resets the
        cached AI suggestions, and reloads the table.
        """
        table_rows: List[BookingRow] = []
    
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

    def _auto_categorize(self) -> None:
        """Request AI category suggestions for all unbooked transactions.

        Shows an indeterminate progress dialog while the request is in
        flight. Shows an informational message if there's nothing to
        categorise, or a critical error dialog if the AI request fails.
        On success, applies the suggestions to the table's category
        combo boxes and shows a summary message.
        """
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

    def _apply_suggestions(self, assignments: Dict[str, int]) -> None:
        """Apply AI-suggested categories to the table's combo boxes.

        Caches ``assignments`` on ``self._ai_suggestions`` so
        :meth:`_book` can later tell which selections came from the AI
        versus the user, and updates each matching row's category combo
        box selection accordingly.

        Args:
            assignments: Mapping of transaction reference to suggested
                category ID, as returned by
                :meth:`ProcessingWindowBackend.get_ai_suggestions`.
        """
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
        """Check whether a transaction reference has more than one row in the table.

        Args:
            reference: The transaction reference to check.

        Returns:
            ``True`` if more than one row's reference cell matches
            ``reference`` (i.e. the transaction has been split into
            multiple parts), ``False`` otherwise.
        """
        count = sum(
            1 for row in range(self.table.rowCount())
            if self.table.item(row, 0) and self.table.item(row, 0).text() == reference
        )
        return count > 1

    def _add_memorial(self) -> None:
        """Open the memorial transaction dialog and save the result if accepted.

        Shows a warning and returns early if no categories exist yet
        (a memorial entry requires selecting both a debit and credit
        category). On confirmation, saves the new memorial transaction
        via the backend and shows a success message.
        """
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

    def _main_screen(self) -> None:
        """Navigate back to the main menu screen."""
        self.stack.setCurrentIndex(0)