# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDoubleSpinBox, QComboBox, QDialogButtonBox, QDateEdit, QMessageBox
)
from PyQt6.QtCore import QDate


class MemorialDialog(QDialog):
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New memorialtransaction")
        self.categories = categories

        layout = QVBoxLayout()
        form = QFormLayout()

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date:", self.date_edit)

        self.description_edit = QLineEdit()
        form.addRow("Description:", self.description_edit)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setMaximum(99999999.99)
        self.amount_spin.setDecimals(2)
        form.addRow("Amount:", self.amount_spin)

        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
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

    def _validate_and_accept(self):
        if self.from_combo.currentData() == self.to_combo.currentData():
            QMessageBox.warning(self, "Invalid entry, same debit and credit category")
            return
        if self.amount_spin.value() <= 0:
            QMessageBox.warning(self, "Invalid entry, amount must be higher than 0")
            return
        self.accept()

    def get_values(self):
        return {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "description": self.description_edit.text().strip(),
            "amount": self.amount_spin.value(),
            "from_category_id": self.from_combo.currentData(),
            "to_category_id": self.to_combo.currentData(),
        }