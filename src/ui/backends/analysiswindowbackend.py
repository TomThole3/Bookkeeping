# -*- coding: utf-8 -*-
"""Backend for the Analysis screen.

This module defines :class:`AnalysisWindowBackend`, which turns booked
transactions from the database into the aggregated data structures consumed
by the chart renderers in ``analysiswindow.py``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Dict, List, Set


from data.database import DatabaseInteractions
from models.transaction import Transaction


class AnalysisWindowBackend:
    """Computes aggregated financial data for the analysis charts.

    Each public ``get_*`` method queries booked transactions within a date
    range and returns a plain ``dict`` shaped for direct use by a specific
    matplotlib chart renderer in :class:`analysiswindow.AnalysisWindow`.

    Attributes:
        db: Database interactions object used to fetch transactions and
            categories.
    """

    def __init__(self, db: "DatabaseInteractions") -> None:
        """Initialise the backend.

        Args:
            db: Database interactions object providing access to booked
                transactions and categories.
        """
        self.db = db

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_transactions_in_range(
        self, date_from: str, date_to: str
    ) -> List["Transaction"]:
        """Fetch all categorised transactions within the date range.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.

        Returns:
            All booked transactions whose ``date`` falls within
            ``[date_from, date_to]`` (transactions with no date are
            treated as sorting before every range and are excluded unless
            ``date_from`` is empty).
        """
        return [
            t for t in self.db.get_booked_transactions()
            if date_from <= (t.date or "") <= date_to 
        ]

    @staticmethod
    def _month_key(date_str: str) -> str:
        """Return the ``'YYYY-MM'`` prefix of a ``'YYYY-MM-DD'`` string.

        Args:
            date_str: A date string formatted as ``"YYYY-MM-DD"``.

        Returns:
            The first 7 characters of ``date_str`` (the year and month).
        """
        return date_str[:7]

    # ── Analysis methods ───────────────────────────────────────────────────

    def get_income_vs_expenditure(self, date_from: str, date_to: str) -> Dict[str, List[Any]]:
        """Compute monthly income and expenditure totals.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.

        Returns:
            A dict shaped as::

                {
                    "months": ["2024-01", "2024-02", ...],
                    "income": [1200.0, 1300.0, ...],
                    "expenditure": [900.0, 1100.0, ...]
                }

            ``months`` is the sorted union of every month that had income
            or expenditure activity; ``income`` and ``expenditure`` are
            aligned to it position-for-position.
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        income: DefaultDict[str, float] = defaultdict(float)
        expenditure: DefaultDict[str, float] = defaultdict(float)

        for t in transactions:
            month = self._month_key(t.date)
            amount = float(t.amount)
            if t.side == "CRDT":
                income[month] += amount
            else:
                expenditure[month] += amount

        months = sorted(set(income) | set(expenditure))
        return {
            "months": months,
            "income": [income[m] for m in months],
            "expenditure": [expenditure[m] for m in months],
        }

    def get_category_breakdown(self, date_from: str, date_to: str) -> Dict[str, List[Any]]:
        """Compute expenditure totals per top-level category.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.

        Returns:
            A dict shaped as::

                {
                    "categories": ["Food", "Transport", ...],
                    "amounts": [450.0, 200.0, ...]
                }

            Entries are sorted by amount, largest first. Only debit
            (``"DBIT"``) transactions are counted.
        """
        transactions = self._get_transactions_in_range(date_from, date_to)
        all_categories = self.db.get_categories()
        cat_map = {c.id: c for c in all_categories}
        
        totals: DefaultDict[str, float] = defaultdict(float)
        for t in transactions:
            if t.side == "DBIT":
                cat = cat_map.get(t.category_id)
                totals[cat.name] += float(t.amount)
        
        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        return {
            "categories": [i[0] for i in sorted_items],
            "amounts": [i[1] for i in sorted_items],
        }

    def get_spending_per_category_over_time(
        self, date_from: str, date_to: str
    ) -> Dict[str, Any]:
        """Compute monthly expenditure per top-level category.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.

        Returns:
            A dict shaped as::

                {
                    "months": ["2024-01", ...],
                    "series": {
                        "Food": [200.0, 180.0, ...],
                        "Transport": [80.0, 95.0, ...],
                        ...
                    }
                }

            ``months`` is the sorted list of months with any expenditure
            activity. Each list in ``series`` is aligned to ``months`` and
            defaults to ``0.0`` for months without spending in that
            category. Only debit (``"DBIT"``) transactions are counted,
            and ``series`` keys are sorted alphabetically by category name.
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        all_categories = self.db.get_categories()
        cat_map = {c.id: c for c in all_categories}

        # {category: {month: amount}}
        data: DefaultDict[str, DefaultDict[str, float]] = defaultdict(lambda: defaultdict(float))
        months_seen: Set[str] = set()

        for t in transactions:
            if t.side == "DBIT":
                month = self._month_key(t.date)
                cat = cat_map.get(t.category_id)
                data[cat.name][month] += float(t.amount)
                months_seen.add(month)

        months = sorted(months_seen)
        return {
            "months": months,
            "series": {
                cat: [data[cat].get(m, 0.0) for m in months]
                for cat in sorted(data)
            },
        }

    def get_top_counterparties(
        self, date_from: str, date_to: str, top_n: int = 15
    ) -> Dict[str, List[Any]]:
        """Compute the top counterparties by total expenditure.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.
            top_n: Maximum number of counterparties to return, ordered by
                expenditure descending. Defaults to 15.

        Returns:
            A dict shaped as::

                {
                    "counterparties": ["Albert Heijn", ...],
                    "amounts": [320.0, ...]
                }

            Only debit (``"DBIT"``) transactions are counted. Transactions
            with no counterparty name are grouped under ``"Unknown"``.
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        totals: DefaultDict[str, float] = defaultdict(float)
        for t in transactions:
            if t.side == "DBIT":
                name = t.counterparty_name or "Unknown"
                totals[name] += float(t.amount)

        sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return {
            "counterparties": [i[0] for i in sorted_items],
            "amounts": [i[1] for i in sorted_items],
        }

    def get_running_balance(self, date_from: str, date_to: str) -> Dict[str, List[Any]]:
        """Compute the cumulative net balance per day.

        Args:
            date_from: Inclusive lower bound, formatted as ``"YYYY-MM-DD"``.
            date_to: Inclusive upper bound, formatted as ``"YYYY-MM-DD"``.

        Returns:
            A dict shaped as::

                {
                    "dates": ["2024-01-01", ...],
                    "balance": [120.0, 95.0, ...]
                }

            ``dates`` is the sorted list of distinct dates with activity.
            ``balance`` is the running (cumulative) net balance —
            credits add, debits subtract — aligned to ``dates``.
        """
        transactions = self._get_transactions_in_range(date_from, date_to)

        # Accumulate net per day
        daily: DefaultDict[str, float] = defaultdict(float)
        for t in transactions:
            amount = float(t.amount)
            if t.side == "CRDT":
                daily[t.date] += amount
            else:
                daily[t.date] -= amount

        dates = sorted(daily)
        balance: List[float] = []
        running = 0.0
        for d in dates:
            running += daily[d]
            balance.append(running)

        return {"dates": dates, "balance": balance}