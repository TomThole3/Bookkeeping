# -*- coding: utf-8 -*-
"""Confirmation dialog for removing a category or deleting a memorial pair."""
from __future__ import annotations
 
import re
from typing import Optional, Protocol
from memorialhelper import MEMORIAL_PREFIX, memorial_base_ref
 
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
 
# ── Constants ────────────────────────────────────────────────────────────
_WARNING_COLOR = "#b05000"
_SPLIT_SUFFIX_RE = re.compile(r"-\d+$")
 
 
class TransactionLike(Protocol):
    """Structural type describing what this dialog needs from a transaction.
 
    Lets the dialog stay decoupled from whatever concrete Transaction
    class the rest of the app uses.
    """
    reference: Optional[str]
    amount: Optional[float]
    date: Optional[str]
    counterparty_name: Optional[str]
    is_split: bool
 
 
class UnbookDialog(QDialog):
    """Confirmation dialog shown before removing a category, or -- for
    memorial transactions -- before deleting both legs of the pair.
    """
 
    def __init__(self, transaction: TransactionLike, parent=None):
        super().__init__(parent)
        self._transaction = transaction
        self._is_memorial = self._reference_is_memorial(transaction.reference)
 
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setWindowTitle(
            "Delete memorial pair" if self._is_memorial else "Unbook"
        )
 
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(self._build_details_frame())
 
        warning_label = self._build_warning_label()
        if warning_label is not None:
            layout.addWidget(warning_label)
 
        layout.addWidget(self._build_question_label())
        layout.addLayout(self._build_button_row())
 
    # ── UI builders ──────────────────────────────────────────────────────
 
    def _build_details_frame(self) -> QFrame:
        transaction = self._transaction
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
 
        frame_layout = QVBoxLayout(frame)
        frame_layout.setSpacing(4)
 
        rows = (
            ("Reference:", transaction.reference or "—"),
            ("Amount:", self._format_amount(transaction.amount)),
            ("Date:", transaction.date or "—"),
            ("Counterparty:", transaction.counterparty_name or "—"),
        )
        for label, value in rows:
            frame_layout.addWidget(self._make_detail_label(label, value))
 
        return frame
 
    @staticmethod
    def _make_detail_label(label: str, value: str) -> QLabel:
        lbl = QLabel(f"<b>{label}</b> {value}")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        return lbl
 
    def _build_warning_label(self) -> Optional[QLabel]:
        """Return the appropriate warning label, or None if none applies."""
        text = self._warning_text()
        if text is None:
            return None
 
        warning = QLabel(text)
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setWordWrap(True)
        warning.setStyleSheet(f"color: {_WARNING_COLOR};")
        return warning
 
    def _warning_text(self) -> Optional[str]:
        transaction = self._transaction
 
        if self._is_memorial:
            base = memorial_base_ref(transaction.reference)
            return (
                "⚠️  This is a memorial transaction. Both legs "
                f"<b>{base}-D</b> and <b>{base}-C</b> will be deleted."
            )
 
        if transaction.is_split:
            prefix = self._split_prefix(transaction.reference)
            return (
                "⚠️  This is a split transaction. All parts matching "
                f"<b>{prefix}-*</b> will be unbooked."
            )
 
        return None
 
    def _build_question_label(self) -> QLabel:
        text = (
            "Delete this memorial pair?"
            if self._is_memorial
            else "Unbook this transaction?"
        )
        question = QLabel(text)
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return question
 
    def _build_button_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addStretch()
 
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)
 
        btn_confirm = QPushButton("Delete pair" if self._is_memorial else "Unbook")
        btn_confirm.setDefault(True)
        btn_confirm.clicked.connect(self.accept)
        row.addWidget(btn_confirm)
 
        return row
 
    # ── Formatting / parsing helpers ────────────────────────────────────
 
    @staticmethod
    def _format_amount(amount: Optional[float]) -> str:
        return f"€ {amount:,.2f}" if amount is not None else "—"
 
    @staticmethod
    def _reference_is_memorial(reference: Optional[str]) -> bool:
        return (reference or "").startswith(MEMORIAL_PREFIX)
 
    @staticmethod
    def _split_prefix(reference: Optional[str]) -> str:
        """Strip the trailing -<n> split-part suffix."""
        return _SPLIT_SUFFIX_RE.sub("", reference or "")