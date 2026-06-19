# -*- coding: utf-8 -*-
from database import DatabaseInteractions

class JournalWindowBackend:
    def __init__(self):
        self.db = DatabaseInteractions()
        self._transactions = []

    def load_transactions(self):
        self._transactions = self.db.get_categorized_transactions()
        self._transactions.sort(key=lambda t: t.date, reverse=True)

    def get_categories(self) -> list[str]:
        return sorted({t.category_id for t in self._transactions if t.category_id})

    def get_filtered_transactions(self, filters: dict) -> list:
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

    @staticmethod
    def _amount_in_range(raw_amount, minimum: float, maximum: float) -> bool:
        try:
            return minimum <= float(raw_amount) <= maximum
        except (TypeError, ValueError):
            return True  # Don't exclude transactions with unparseable amounts

    @staticmethod
    def _date_in_range(raw_date: str, date_from: str, date_to: str) -> bool:
        if not raw_date:
            return True  # Don't exclude transactions with missing dates
        try:
            return date_from <= raw_date <= date_to  # ISO strings compare correctly
        except TypeError:
            return True