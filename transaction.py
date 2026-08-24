# -*- coding: utf-8 -*-
"""Transaction domain model.

This module defines :class:`Transaction`, the core data object
representing a single bookkeeping entry — either an imported bank
transaction (or one of its split parts), or a leg of a manual memorial
entry.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class Transaction:
    """A single bookkeeping transaction.

    Instances are constructed either directly (e.g. from database rows
    or UI table data) or via :meth:`from_dict` from a raw CAMT entry
    dict produced by :class:`camt_parser.CAMTParser`.

    Attributes:
        reference: Unique identifier for this transaction. For split
            parts this includes a ``-N`` suffix; for memorial legs it
            includes a ``-D`` / ``-C`` suffix.
        amount: The transaction amount (always non-negative; direction
            is conveyed by ``side``).
        side: ``"CRDT"`` for a credit (incoming) or ``"DBIT"`` for a
            debit (outgoing) transaction.
        date: Booking date, formatted as ``"YYYY-MM-DD"``.
        description: Free-text description or additional entry
            information.
        counterparty_name: Name of the other party in the transaction,
            or ``None`` if unavailable.
        counterparty_iban: IBAN of the other party, or ``None`` if
            unavailable.
        category_id: ID of the category this transaction has been
            assigned to, or ``None`` if not yet categorised.
        is_split: ``1`` (truthy) if this transaction has been divided
            into multiple booked parts, ``0`` otherwise.
    """

    def __init__(
        self,
        reference: Optional[str],
        amount: float,
        side: Optional[str],
        date: Optional[str],
        description: Optional[str],
        counterparty_name: Optional[str],
        counterparty_iban: Optional[str],
        category_id: Optional[int] = None,
        is_split: int = 0,
    ) -> None:
        """Initialise a transaction.

        Args:
            reference: Unique identifier for this transaction.
            amount: The transaction amount.
            side: ``"CRDT"`` or ``"DBIT"``.
            date: Booking date, formatted as ``"YYYY-MM-DD"``.
            description: Free-text description, if any.
            counterparty_name: Name of the counterparty, if known.
            counterparty_iban: IBAN of the counterparty, if known.
            category_id: ID of the assigned category, or ``None`` if
                uncategorised. Defaults to ``None``.
            is_split: Whether this transaction has been split into
                multiple parts (``1``) or not (``0``). Defaults to
                ``0``.
        """
        self.reference: Optional[str] = reference
        self.amount: float = amount
        self.side: Optional[str] = side
        self.date: Optional[str] = date
        self.description: Optional[str] = description
        self.counterparty_name: Optional[str] = counterparty_name
        self.counterparty_iban: Optional[str] = counterparty_iban
        self.category_id: Optional[int] = category_id
        self.is_split: int = is_split

    @classmethod
    def from_dict(cls, entry: Dict[str, Any]) -> "Transaction":
        """Build a Transaction from a raw, normalised CAMT entry dict.

        Args:
            entry: A dict as produced by
                :meth:`camt_parser.CAMTParser.normalize_counterparty`,
                expected to contain ``"NtryRef"``, ``"Amount"``,
                ``"CdtDbtInd"``, ``"BookgDt"``, ``"AddtlNtryInf"``, and
                optionally ``"Counterparty_Name"`` /
                ``"Counterparty_IBAN"``.

        Returns:
            A new :class:`Transaction` with ``category_id`` and
            ``is_split`` left at their defaults (``None`` and ``0``),
            since a freshly parsed bank entry is always unbooked.
        """
        return cls(
            reference=entry["NtryRef"],
            amount=float(entry["Amount"]),
            side=entry["CdtDbtInd"],
            date=entry["BookgDt"],
            description=entry["AddtlNtryInf"],
            counterparty_name=entry.get("Counterparty_Name"),
            counterparty_iban=entry.get("Counterparty_IBAN")
        )

    def __repr__(self) -> str:
        """Return a debug string showing the transaction's reference."""
        return ", ".join([
            str(self.reference),
        ])