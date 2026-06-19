# -*- coding: utf-8 -*-
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt


class RemoveCategoryDialog(QDialog):
    """
    Confirmation dialog shown before removing a category from a transaction.
    Displays key transaction details and warns the user if the transaction
    is part of a split (all parts will be affected).
    """

    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove category")
        self.setModal(True)
        self.setMinimumWidth(380)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # ── Transaction details ────────────────────────────────────────────
        details = QFrame()
        details.setFrameShape(QFrame.Shape.StyledPanel)
        details_layout = QVBoxLayout(details)
        details_layout.setSpacing(4)

        def detail_row(label: str, value: str):
            lbl = QLabel(f"<b>{label}</b> {value}")
            lbl.setTextFormat(Qt.TextFormat.RichText)
            details_layout.addWidget(lbl)

        detail_row("Reference:", transaction.reference or "—")
        detail_row("Amount:", f"€ {transaction.amount:,.2f}" if transaction.amount is not None else "—")
        detail_row("Date:", transaction.date or "—")
        detail_row("Counterparty:", transaction.counterparty_name or "—")

        layout.addWidget(details)

        # ── Split warning ──────────────────────────────────────────────────
        if transaction.is_split:
            prefix = _split_prefix(transaction.reference)
            warning = QLabel(
                f"⚠️  This is a split transaction. All parts matching "
                f"<b>{prefix}-*</b> will have their category removed."
            )
            warning.setTextFormat(Qt.TextFormat.RichText)
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #b05000;")
            layout.addWidget(warning)

        # ── Question ───────────────────────────────────────────────────────
        question = QLabel("Remove the category from this transaction?")
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(question)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("Remove category")
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)
        self.setLayout(layout)


def _split_prefix(reference: str) -> str:
    """Strip the trailing -{integer} suffix to get the shared split prefix."""
    return re.sub(r"-\d+$", "", reference or "")
