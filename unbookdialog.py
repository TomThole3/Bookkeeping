# -*- coding: utf-8 -*-
"""Confirmation dialog for removing a category or deleting a memorial pair.

This module defines :class:`UnbookDialog`, shown before a transaction is
unbooked (its category cleared) from the Journal or Balance drill-down
screens. It adapts its wording and warnings depending on whether the
transaction is a normal booking, part of a split transaction, or one leg
of a memorial (manual journal) entry.
"""
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
    QWidget,
)
 
# ── Constants ────────────────────────────────────────────────────────────

#: Text colour used for the split/memorial warning label.
_WARNING_COLOR = "#b05000"

#: Matches a trailing "-<n>" split-part suffix on a reference (e.g. the
#: "-2" in "ABC123-2").
_SPLIT_SUFFIX_RE = re.compile(r"-\d+$")
 
 
class TransactionLike(Protocol):
    """Structural type describing what this dialog needs from a transaction.
 
    Lets the dialog stay decoupled from whatever concrete Transaction
    class the rest of the app uses.

    Attributes:
        reference: Unique identifier for the transaction, or ``None``.
        amount: The transaction amount, or ``None``.
        date: Booking date as ``"YYYY-MM-DD"``, or ``None``.
        counterparty_name: Name of the counterparty, or ``None``.
        is_split: Whether this transaction has been divided into
            multiple booked parts.
    """
    reference: Optional[str]
    amount: Optional[float]
    date: Optional[str]
    counterparty_name: Optional[str]
    is_split: bool
 
 
class UnbookDialog(QDialog):
    """Confirmation dialog shown before removing a category, or -- for
    memorial transactions -- before deleting both legs of the pair.

    The dialog always shows the transaction's key details (reference,
    amount, date, counterparty). If the transaction is a memorial leg or
    a split part, an additional warning explains the wider scope of the
    action (both legs deleted, or all split parts unbooked,
    respectively) before asking the user to confirm.

    Attributes:
        DialogCode: Inherited from :class:`QDialog`; ``exec()`` returns
            ``DialogCode.Accepted`` if the user confirms, or
            ``DialogCode.Rejected`` (via Cancel) otherwise.
    """
 
    def __init__(self, transaction: TransactionLike, parent: Optional[QWidget] = None) -> None:
        """Initialise the dialog for a specific transaction.

        Args:
            transaction: The transaction being considered for unbooking
                (or, if a memorial leg, for pair deletion). Only the
                fields described by :class:`TransactionLike` are used.
            parent: Optional parent widget for the dialog.
        """
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
        """Build the panel showing the transaction's key details.

        Returns:
            A styled :class:`QFrame` containing one label per detail
            row: reference, amount, date, and counterparty (each
            falling back to an em dash when the underlying value is
            missing).
        """
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
        """Build a single bold-label/value row for the details panel.

        Args:
            label: The bold field name (e.g. ``"Reference:"``).
            value: The value to display next to the label.

        Returns:
            A rich-text :class:`QLabel` rendering ``"<b>label</b> value"``.
        """
        lbl = QLabel(f"<b>{label}</b> {value}")
        lbl.setTextFormat(Qt.TextFormat.RichText)
        return lbl
 
    def _build_warning_label(self) -> Optional[QLabel]:
        """Return the appropriate warning label, or None if none applies.

        Returns:
            A word-wrapped, coloured :class:`QLabel` describing the
            wider scope of the action (memorial pair or split parts),
            or ``None`` if the transaction is a plain, unsplit booking
            and no extra warning is needed.
        """
        text = self._warning_text()
        if text is None:
            return None
 
        warning = QLabel(text)
        warning.setTextFormat(Qt.TextFormat.RichText)
        warning.setWordWrap(True)
        warning.setStyleSheet(f"color: {_WARNING_COLOR};")
        return warning
 
    def _warning_text(self) -> Optional[str]:
        """Determine the warning message text, if any, for this transaction.

        Returns:
            Rich-text warning explaining that both memorial legs will
            be deleted, or that all split parts will be unbooked. Returns
            ``None`` if the transaction is neither a memorial leg nor a
            split part.
        """
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
        """Build the centered confirmation question label.

        Returns:
            A :class:`QLabel` asking either "Delete this memorial
            pair?" or "Unbook this transaction?", depending on the
            transaction type.
        """
        text = (
            "Delete this memorial pair?"
            if self._is_memorial
            else "Unbook this transaction?"
        )
        question = QLabel(text)
        question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return question
 
    def _build_button_row(self) -> QHBoxLayout:
        """Build the Cancel / confirm button row.

        Returns:
            A right-aligned :class:`QHBoxLayout` containing a "Cancel"
            button (wired to :meth:`reject`) and a confirm button
            (labelled "Delete pair" or "Unbook" as appropriate, wired
            to :meth:`accept` and set as the dialog's default button).
        """
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
        """Format an amount as a Euro-denominated string.

        Args:
            amount: The numeric amount to format, or ``None``.

        Returns:
            The amount formatted as e.g. ``"€ 1,234.56"``, or an em
            dash (``"—"``) if ``amount`` is ``None``.
        """
        return f"€ {amount:,.2f}" if amount is not None else "—"
 
    @staticmethod
    def _reference_is_memorial(reference: Optional[str]) -> bool:
        """Check whether a reference belongs to a memorial transaction leg.

        Args:
            reference: The transaction reference to check, or ``None``.

        Returns:
            ``True`` if ``reference`` starts with
            :data:`memorialhelper.MEMORIAL_PREFIX`, ``False`` otherwise
            (including when ``reference`` is ``None``).
        """
        return (reference or "").startswith(MEMORIAL_PREFIX)
 
    @staticmethod
    def _split_prefix(reference: Optional[str]) -> str:
        """Strip the trailing -<n> split-part suffix.

        Args:
            reference: A split part's reference (e.g. ``"ABC123-2"``),
                or ``None``.

        Returns:
            ``reference`` with any trailing ``"-<digits>"`` suffix
            removed (e.g. ``"ABC123"``), or an empty string if
            ``reference`` is ``None``.
        """
        return _SPLIT_SUFFIX_RE.sub("", reference or "")