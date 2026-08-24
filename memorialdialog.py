# -*- coding: utf-8 -*-
"""Memorial (manual journal) transaction dialog.

This module defines :class:`MemorialDialog`, a modal dialog for creating
a manual "memorial" transaction — a two-legged journal entry that debits
one category and credits another for the same amount.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QDialogButtonBox, QDateEdit, QMessageBox,
    QWidget,
)
from PyQt6.QtCore import QDate

if TYPE_CHECKING:
    # Only needed for type-checking; avoids a hard runtime dependency/
    # circular import on the concrete Category class.
    from category import Category

# The dict returned by get_values(): date/description are strings, amount
# is a float, and the category IDs are ints (or None if nothing was
# selectable, though the combo boxes are always populated when categories
# exist).
MemorialValues = Dict[str, Union[str, float, Optional[int]]]


class MemorialDialog(QDialog):
    """Modal dialog for entering a new memorial (manual journal) transaction.

    Presents a form for the date, description, and amount, plus two
    category dropdowns: the category debited (money "from") and the
    category credited (money "to"). Confirms that the two categories
    differ before allowing the dialog to be accepted.

    Attributes:
        date_edit: Date picker for the transaction date, defaulting to
            today.
        description_edit: Free-text field for the transaction
            description.
        amount_spin: Spin box for the transaction amount.
        from_combo: Dropdown selecting the debited ("from") category.
        to_combo: Dropdown selecting the credited ("to") category.
    """

    def __init__(self, categories: List["Category"], parent: Optional[QWidget] = None) -> None:
        """Initialise the dialog and populate the category dropdowns.

        Args:
            categories: The categories available to select as the debit
                ("from") or credit ("to") side of the entry. Both
                dropdowns are populated with the full list.
            parent: Optional parent widget for the dialog.
        """
        super().__init__(parent)
        self.setWindowTitle("New memorialtransaction")

        layout = QVBoxLayout()
        form = QFormLayout()

        self.date_edit: QDateEdit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date:", self.date_edit)

        self.description_edit: QLineEdit = QLineEdit()
        form.addRow("Description:", self.description_edit)

        self.amount_spin: QDoubleSpinBox = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99999999.99)
        self.amount_spin.setDecimals(2)
        form.addRow("Amount:", self.amount_spin)

        self.from_combo: QComboBox = QComboBox()
        self.to_combo: QComboBox = QComboBox()
        for cat in categories:
            self.from_combo.addItem(cat.name, cat.id)
            self.to_combo.addItem(cat.name, cat.id)
        form.addRow("From category (debit):", self.from_combo)
        form.addRow("To category (credit):", self.to_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _validate_and_accept(self) -> None:
        """Validate the form and accept the dialog if valid.

        Shows a warning message box and refuses to accept if the debit
        and credit categories are the same; otherwise accepts the
        dialog (equivalent to clicking "OK").
        """
        if self.from_combo.currentData() == self.to_combo.currentData():
            QMessageBox.warning(self, "Invalid entry", "Debit and credit category cannot be the same.")
            return
        self.accept()   

    def get_values(self) -> MemorialValues:
        """Collect the entered form values.

        Returns:
            A dict shaped as::

                {
                    "date": "YYYY-MM-DD",
                    "description": str,
                    "amount": float,
                    "from_category_id": int,
                    "to_category_id": int,
                }

            Intended to be called after :meth:`exec` returns
            ``QDialog.DialogCode.Accepted``.
        """
        return {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "from_category_id": self.from_combo.currentData(),
            "to_category_id": self.to_combo.currentData(),
        }