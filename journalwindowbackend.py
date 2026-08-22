# -*- coding: utf-8 -*-
import re
from memorialhelper import memorial_base_ref, MEMORIAL_PREFIX
from category import Category


class JournalWindowBackend:
    def __init__(self, db):
        self.db = db
        self._transactions = []

    # ── Data loading ───────────────────────────────────────────────────────

    def load_transactions(self):
        """Fetch all transactions from the database, cache them sorted latest first."""
        self._transactions = self.db.get_categorized_transactions()
        self._transactions.sort(key=lambda t: t.date or "", reverse=True)

    # ── Queries ────────────────────────────────────────────────────────────

    def get_category_ids(self) -> list[int]:
        """Return a sorted list of unique category IDs present in the loaded transactions."""
        return sorted({t.category_id for t in self._transactions if t.category_id})

    def get_filtered_transactions(self, filters: dict) -> list:
        """
        Return transactions matching all active filters.

        Expected filter keys (all optional / nullable):
            reference    (str)  – case-insensitive substring match
            side      (str)  – exact match; "All" means no filter
            category     (str)  – exact match; "All" means no filter
            counterparty (str)  – case-insensitive substring match
            description  (str)  – case-insensitive substring match
            amount_min   (float)
            amount_max   (float)
            date_from    (str)  – "YYYY-MM-DD"
            date_to      (str)  – "YYYY-MM-DD"
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

        result = []
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
    
    def get_category_map(self):
        return Category.build_map(self.db.get_categories())

    # ── Mutations ──────────────────────────────────────────────────────────

    def remove_category(self, transaction) -> None:
        if transaction.is_split:
            prefix = re.sub(r"-\d+$", "", transaction.reference or "")
            self.db.remove_split_parts(prefix)
        else:
            self.db.remove_category_by_reference(transaction.reference)
            
    def delete_memorial_pair(self, transaction) -> None:
        base = memorial_base_ref(transaction.reference)
        self.db.delete_memorial_pair(f"{base}-D", f"{base}-C")
        
    def remove_transaction(self, transaction):
        if transaction.reference.startswith(MEMORIAL_PREFIX):
            self.delete_memorial_pair(transaction)
        else:
            self.remove_category(transaction)
            
    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _amount_in_range(raw_amount, minimum: float, maximum: float) -> bool:
        try:
            return minimum <= float(raw_amount) <= maximum
        except (TypeError, ValueError):
            return True

    @staticmethod
    def _date_in_range(raw_date: str, date_from: str, date_to: str) -> bool:
        if not raw_date:
            return True
        try:
            return date_from <= raw_date <= date_to
        except TypeError:
            return True