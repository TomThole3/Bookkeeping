# -*- coding: utf-8 -*-
import re
from category import Category
from memorialhelper import memorial_base_ref, MEMORIAL_PREFIX

class CategoryTotals:
    """Holds computed income/expenditure/net for one category (descendants included)."""
    def __init__(self):
        self.income = 0.0
        self.expenditure = 0.0

    @property
    def total(self) -> float:
        return self.income - self.expenditure

    def add(self, other: "CategoryTotals"):
        self.income += other.income
        self.expenditure += other.expenditure


class BalanceWindowBackend:
    def __init__(self, db):
        self.db = db

    def get_category_tree_with_totals(self) -> list:
        """
        Return root Category objects with a `totals` attribute (CategoryTotals)
        attached to every node, rolling up all descendant transactions.
        """
        categories = self.db.get_categories()
        transactions = self.db.get_booked_transactions()

        roots = Category.build_tree(categories)
        category_map = {c.id: c for c in categories}

        for c in categories:
            c.totals = CategoryTotals()

        for t in transactions:
            if t.category_id and t.category_id in category_map:
                cat = category_map[t.category_id]
                try:
                    amount = float(t.amount)
                except (TypeError, ValueError):
                    amount = 0.0
                if t.side == "CRDT":
                    cat.totals.income += amount
                else:
                    cat.totals.expenditure += amount

        for root in roots:
            self._roll_up(root)

        return roots

    def get_transactions_for_category(self, category_id: int) -> list:
        """Return only the direct transactions belonging to this category."""
        return self.db.get_transactions_by_category(category_id)

    # ── Mutations ──────────────────────────────────────────────────────────

    def remove_category(self, transaction) -> None:
        if transaction.is_split:
            prefix = re.sub(r"-\d+$", "", transaction.reference or "")
            self.db.unbook_split_parts(prefix)
        else:
            self.db.unbook_by_reference(transaction.reference)
            
    def delete_memorial_pair(self, transaction) -> None:
        base = memorial_base_ref(transaction.reference)
        self.db.delete_memorial_pair(f"{base}-D", f"{base}-C")
        
    def unbook_transaction(self, transaction):
        if transaction.reference and transaction.reference.startswith(MEMORIAL_PREFIX):
            self.delete_memorial_pair(transaction)
        else:
            self.remove_category(transaction)

    # ── Private helpers ────────────────────────────────────────────────────

    def _roll_up(self, node) -> CategoryTotals:
        """Recursively add children's totals into the parent and return the result."""
        for child in node.children:
            child_totals = self._roll_up(child)
            node.totals.add(child_totals)
        return node.totals