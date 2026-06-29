# -*- coding: utf-8 -*-
import re
from database import DatabaseInteractions
from memorialhelper import memorial_prefix, memorial_base_ref, next_memorial_index, build_memorial_refs


class JournalWindowBackend:
    def __init__(self):
        self.db = DatabaseInteractions()
        self._transactions = []

    # ── Data loading ───────────────────────────────────────────────────────

    def load_transactions(self):
        """Fetch all transactions from the database, cache them sorted latest first."""
        self._transactions = self.db.get_categorized_transactions()
        self._transactions.sort(key=lambda t: t.date or "", reverse=True)

    # ── Queries ────────────────────────────────────────────────────────────

    def get_categories(self) -> list[str]:
        """Return a sorted list of unique category IDs present in the loaded transactions."""
        return sorted({t.category_id for t in self._transactions if t.category_id})

    def get_filtered_transactions(self, filters: dict) -> list:
        """
        Return transactions matching all active filters.

        Expected filter keys (all optional / nullable):
            reference    (str)  – case-insensitive substring match
            cdt_dbt      (str)  – exact match; "All" means no filter
            category     (str)  – exact match; "All" means no filter
            counterparty (str)  – case-insensitive substring match
            description  (str)  – case-insensitive substring match
            amount_min   (float)
            amount_max   (float)
            date_from    (str)  – "YYYY-MM-DD"
            date_to      (str)  – "YYYY-MM-DD"
        """
        reference    = (filters.get("reference") or "").lower()
        cdt_dbt      = filters.get("cdt_dbt", "All")
        category     = filters.get("category", "All")
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
            if cdt_dbt != "All" and t.cdt_dbt != cdt_dbt:
                continue
            if category != "All" and (t.category_id or "") != category:
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

    # ── Mutations ──────────────────────────────────────────────────────────

    def remove_category(self, transaction) -> None:
        if transaction.is_split:
            prefix = re.sub(r"-\d+$", "", transaction.reference or "")
            self.db.remove_split_parts(prefix)
        else:
            self.db.remove_category_by_reference(transaction.reference)

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
        
    def delete_memorial_pair(self, transaction) -> None:
        base = memorial_base_ref(transaction.reference)
        self.db.delete_memorial_pair(f"{base}-D", f"{base}-C")