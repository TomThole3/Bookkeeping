# -*- coding: utf-8 -*-
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
)
from PyQt6.QtCore import Qt


def _split_prefix(reference: str) -> str:
    return re.sub(r"-\d+$", "", reference or "")


class RemoveCategoryDialog(QDialog):
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setMinimumWidth(380)

        is_mem = self._is_memorial(transaction.reference)
        self.setWindowTitle("Delete memorial pair" if is_mem else "Remove category")

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

        # ── Warning ────────────────────────────────────────────────────────
        if is_mem:
            base = self._memorial_base_ref(transaction.reference)
            warning = QLabel(
                f"⚠️  This is a memorial transaction. Both legs "
                f"<b>{base}-D</b> and <b>{base}-C</b> will be deleted."
            )
            warning.setTextFormat(Qt.TextFormat.RichText)
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #b05000;")
            layout.addWidget(warning)
        elif transaction.is_split:
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
        question = QLabel(
            "Delete this memorial pair?" if is_mem
            else "Remove the category from this transaction?"
        )
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(question)

        # ── Buttons ────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_confirm = QPushButton("Delete pair" if is_mem else "Remove category")
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self.accept)
        btn_row.addWidget(btn_confirm)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    # ── Static helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _is_memorial(reference: str) -> bool:
        return (reference or "").startswith("MEM-")

    @staticmethod
    def _memorial_base_ref(reference: str) -> str:
        """Strip the trailing -D or -C leg suffix."""
        return re.sub(r"-[DC]$", "", reference or "")