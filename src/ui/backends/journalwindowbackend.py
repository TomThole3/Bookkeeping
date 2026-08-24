# -*- coding: utf-8 -*-
"""Backend for the Journal screen.

This module defines :class:`JournalWindowBackend`, which loads and
caches booked transactions, applies the Journal screen's filters, and
performs unbook operations (including cascading to split parts and
memorial pairs).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from util.memorialhelper import memorial_base_ref, MEMORIAL_PREFIX
from models.category import Category

from data.database import DatabaseInteractions
from models.transaction import Transaction


class JournalWindowBackend:
    """Loads, filters, and mutates booked transactions for the Journal screen.

    Transactions are fetched once via :meth:`load_transactions` and
    cached (sorted latest first); all filtering happens in-memory
    against that cache until the next reload.

    Attributes:
        db: Database interactions object used for persistence.
    """

    def __init__(self, db: "DatabaseInteractions") -> None:
        """Initialise the backend with an empty transaction cache.

        Args:
            db: Database interactions object used for persistence.
        """
        self.db = db
        self._transactions: List["Transaction"] = []

    # ── Data loading ───────────────────────────────────────────────────────

    def load_transactions(self) -> None:
        """Fetch all transactions from the database, cache them sorted latest first."""
        self._transactions = self.db.get_booked_transactions()
        self._transactions.sort(key=lambda t: t.date or "", reverse=True)

    # ── Queries ────────────────────────────────────────────────────────────

    def get_category_ids(self) -> List[int]:
        """Return a sorted list of unique category IDs present in the loaded transactions."""
        return sorted({t.category_id for t in self._transactions if t.category_id})

    def get_filtered_transactions(self, filters: Dict[str, Any]) -> List["Transaction"]:
        """
        Return transactions matching all active filters.

        Expected filter keys (all optional / nullable):
            reference    (str)  – case-insensitive substring match
            side      (str)  – exact match; "All" means no filter
            category_id  (int | None) – exact match; None means no filter
            counterparty (str)  – case-insensitive substring match
            description  (str)  – case-insensitive substring match
            amount_min   (float)
            amount_max   (float)
            date_from    (str)  – "YYYY-MM-DD"
            date_to      (str)  – "YYYY-MM-DD"

        Args:
            filters: Dict of filter values as described above. All keys
                are optional; missing keys fall back to "no filter"
                defaults.

        Returns:
            The subset of the cached (loaded) transactions that match
            every active filter, in their existing (latest-first) order.
        """
        reference    = (filters.get("reference") or "").lower()
        side      = filters.get("side", "All")
        category_id = filters.get("category_id")
        counterparty = (filters.get("counterparty") or "").lower()
        description  = (filters.get("description") or "").lower()
        amount_min   = filters.get("amount_min", 0)
        amount_max   = filters.get("amount_max", 999_999_999)
        date_from    = filters.get("date_from", "1900-01-01")
        date_to      = filters.get("date_to", "2100-12-31")

        result: List["Transaction"] = []
        for t in self._transactions:
            if reference and reference not in (t.reference or "").lower():
                continue
            if side != "All" and t.side != side:
                continue
            if category_id is not None and t.category_id != category_id:
                continue
            if counterparty and counterparty not in (t.counterparty_name or "").lower():
                continue
            if description and description not in (t.description or "").lower():
                continue
            if not self._amount_in_range(t.amount, amount_min, amount_max):
                continue
            if not self._date_in_range(t.date, date_from, date_to):
                continue
            result.append(t)

        return result

    def get_category_map(self) -> Dict[int, str]:
        """Return a lookup of category ID to category name.

        Returns:
            A dict mapping each category's ``id`` to its ``name``, for
            every category currently in the database (used to populate
            the Journal's category filter dropdown and render category
            names in the transaction table).
        """
        return Category.build_map(self.db.get_categories())

    # ── Mutations ──────────────────────────────────────────────────────────

    def remove_category(self, transaction: "Transaction") -> None:
        """Clear the category of a transaction, cascading to split parts.

        Args:
            transaction: The transaction to decategorise. If it's a
                split transaction (``is_split`` is truthy), every part
                matching its reference prefix is unbooked; otherwise
                only the single transaction is decategorised.
        """
        if transaction.is_split:
            prefix = re.sub(r"-\d+$", "", transaction.reference or "")
            self.db.unbook_split_parts(prefix)
        else:
            self.db.unbook_by_reference(transaction.reference)

    def delete_memorial_pair(self, transaction: "Transaction") -> None:
        """Delete both legs of the memorial transaction a leg belongs to.

        Args:
            transaction: Either leg of the memorial pair to delete; its
                base reference is derived and used to delete both the
                ``-D`` and ``-C`` legs.
        """
        base = memorial_base_ref(transaction.reference)
        self.db.delete_memorial_pair(f"{base}-D", f"{base}-C")

    def unbook_transaction(self, transaction: "Transaction") -> None:
        """Unbook a transaction, routing to the appropriate removal logic.

        Args:
            transaction: The transaction to unbook. If its reference
                indicates a memorial leg, both legs of the pair are
                deleted via :meth:`delete_memorial_pair`; otherwise its
                category is cleared via :meth:`remove_category`
                (cascading to split parts if applicable).
        """
        if transaction.reference.startswith(MEMORIAL_PREFIX):
            self.delete_memorial_pair(transaction)
        else:
            self.remove_category(transaction)

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _amount_in_range(raw_amount: Any, minimum: float, maximum: float) -> bool:
        """Check whether an amount falls within an inclusive range.

        Args:
            raw_amount: The amount to check; coerced to ``float``.
            minimum: Inclusive lower bound.
            maximum: Inclusive upper bound.

        Returns:
            ``True`` if ``minimum <= float(raw_amount) <= maximum``.
            Also returns ``True`` (i.e. treats the row as a non-match
            for filtering purposes, letting it through) if
            ``raw_amount`` can't be converted to ``float``.
        """
        try:
            return minimum <= float(raw_amount) <= maximum
        except (TypeError, ValueError):
            return True

    @staticmethod
    def _date_in_range(raw_date: Optional[str], date_from: str, date_to: str) -> bool:
        """Check whether a date string falls within an inclusive range.

        Args:
            raw_date: The date to check, formatted as ``"YYYY-MM-DD"``,
                or falsy (e.g. ``None``/empty).
            date_from: Inclusive lower bound, formatted as
                ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as
                ``"YYYY-MM-DD"``.

        Returns:
            ``True`` if ``raw_date`` is falsy (missing dates are never
            filtered out) or if ``date_from <= raw_date <= date_to``.
            Also returns ``True`` if the comparison raises
            ``TypeError``.
        """
        if not raw_date:
            return True
        try:
            return date_from <= raw_date <= date_to
        except TypeError:
            return True