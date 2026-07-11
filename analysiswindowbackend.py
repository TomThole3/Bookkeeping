# -*- coding: utf-8 -*-
from collections import defaultdict
from database import DatabaseInteractions


class AnalysisWindowBackend:
    def __init__(self):
        self.db = DatabaseInteractions()

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_transactions_in_range(self, date_from: str, date_to: str) -> list:
        """Fetch all categorised transactions within the date range."""
        return [
            t for t in self.db.get_categorized_transactions()
            if date_from <= (t.date or "") <= date_to 
        ]

    @staticmethod
    def _month_key(date_str: str) -> str:
        """Return 'YYYY-MM' from a 'YYYY-MM-DD' string."""
        return date_str[:7]

    # ── Analysis methods ───────────────────────────────────────────────────

    def get_income_vs_expenditure(self, date_from: str, date_to: str) -> dict:
        """
        Returns monthly income and expenditure totals.
        {
            "months": ["2024-01", "2024-02", ...],
            "income": [1200.0, 1300.0, ...],
            "expenditure": [900.0, 1100.0, ...]
        }
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        income = defaultdict(float)
        expenditure = defaultdict(float)

        for t in transactions:
            month = self._month_key(t.date)
            try:
                amount = float(t.amount)
            except (TypeError, ValueError):
                continue
            if t.cdt_dbt == "CRDT":
                income[month] += amount
            else:
                expenditure[month] += amount

        months = sorted(set(income) | set(expenditure))
        return {
            "months": months,
            "income": [income[m] for m in months],
            "expenditure": [expenditure[m] for m in months],
        }

    def get_category_breakdown(self, date_from: str, date_to: str) -> dict:
        """
        Returns expenditure totals per top-level category.
        {
            "categories": ["Food", "Transport", ...],
            "amounts": [450.0, 200.0, ...]
        }
        """
        transactions = self._get_transactions_in_range(date_from, date_to)
        all_categories = self.db.get_categories()
        cat_map = {c.id: c for c in all_categories}
        
        totals = defaultdict(float)
        for t in transactions:
            if t.cdt_dbt == "DBIT":
                try:
                    cat = cat_map.get(t.category_id)
                    cat_name = cat.name if cat else "Unknown"
                    totals[cat_name] += float(t.amount)
                except (TypeError, ValueError):
                    continue
        
        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        return {
            "categories": [i[0] for i in sorted_items],
            "amounts": [i[1] for i in sorted_items],
        }

    def get_spending_per_category_over_time(self, date_from: str, date_to: str) -> dict:
        """
        Returns monthly expenditure per top-level category.
        {
            "months": ["2024-01", ...],
            "series": {
                "Food": [200.0, 180.0, ...],
                "Transport": [80.0, 95.0, ...],
                ...
            }
        }
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        all_categories = self.db.get_categories()
        cat_map = {c.id: c for c in all_categories}

        # {category: {month: amount}}
        data = defaultdict(lambda: defaultdict(float))
        months_seen = set()

        for t in transactions:
            if t.cdt_dbt == "DBIT":
                try:
                    month = self._month_key(t.date)
                    cat = cat_map.get(t.category_id)
                    cat_name = cat.name if cat else "Unknown"
                    data[cat_name][month] += float(t.amount)
                    months_seen.add(month)
                except (TypeError, ValueError):
                    continue

        months = sorted(months_seen)
        return {
            "months": months,
            "series": {
                cat: [data[cat].get(m, 0.0) for m in months]
                for cat in sorted(data)
            },
        }

    def get_top_counterparties(self, date_from: str, date_to: str, top_n: int = 15) -> dict:
        """
        Returns the top N counterparties by total expenditure.
        {
            "counterparties": ["Albert Heijn", ...],
            "amounts": [320.0, ...]
        }
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        totals = defaultdict(float)
        for t in transactions:
            if t.cdt_dbt == "DBIT":
                try:
                    name = t.counterparty_name or "Unknown"
                    totals[name] += float(t.amount)
                except (TypeError, ValueError):
                    continue

        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return {
            "counterparties": [i[0] for i in sorted_items],
            "amounts": [i[1] for i in sorted_items],
        }

    def get_running_balance(self, date_from: str, date_to: str) -> dict:
        """
        Returns the cumulative net balance per day.
        {
            "dates": ["2024-01-01", ...],
            "balance": [120.0, 95.0, ...]
        }
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        # Accumulate net per day
        daily = defaultdict(float)
        for t in transactions:
            try:
                amount = float(t.amount)
            except (TypeError, ValueError):
                continue
            if t.cdt_dbt == "CRDT":
                daily[t.date] += amount
            else:
                daily[t.date] -= amount

        dates = sorted(daily)
        balance = []
        running = 0.0
        for d in dates:
            running += daily[d]
            balance.append(running)

        return {"dates": dates, "balance": balance}
