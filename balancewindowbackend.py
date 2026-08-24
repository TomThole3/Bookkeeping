# -*- coding: utf-8 -*-
"""Backend for the Balance screen.

This module defines :class:`CategoryTotals`, a small value object holding
rolled-up income/expenditure figures for one category, and
:class:`BalanceWindowBackend`, which builds the category tree with
totals attached, fetches per-category transactions for drill-down, and
performs unbook operations (mirroring the Journal screen's, but scoped
to the Balance screen's data flow).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

from category import Category
from memorialhelper import memorial_base_ref, MEMORIAL_PREFIX

if TYPE_CHECKING:
    # Only needed for type-checking; avoids hard runtime dependencies/
    # circular imports on the concrete database and transaction classes.
    from database import DatabaseInteractions
    from transaction import Transaction


class CategoryTotals:
    """Holds computed income/expenditure/net for one category (descendants included).

    Instances are attached to :class:`Category` nodes as their
    ``totals`` attribute by
    :meth:`BalanceWindowBackend.get_category_tree_with_totals`, and
    rolled up from children to parents via :meth:`add`.

    Attributes:
        income: Total credit (``"CRDT"``) amount for this category,
            including all descendant categories once rolled up.
        expenditure: Total debit (``"DBIT"``) amount for this category,
            including all descendant categories once rolled up.
    """

    def __init__(self) -> None:
        """Initialise a zeroed totals object."""
        self.income: float = 0.0
        self.expenditure: float = 0.0

    @property
    def total(self) -> float:
        """The net balance for this category: income minus expenditure."""
        return self.income - self.expenditure

    def add(self, other: "CategoryTotals") -> None:
        """Add another totals object's figures into this one, in place.

        Args:
            other: The totals to merge in (e.g. a child category's
                rolled-up totals being merged into its parent).
        """
        self.income += other.income
        self.expenditure += other.expenditure


class BalanceWindowBackend:
    """Computes category totals and handles unbook operations for the Balance screen.

    Attributes:
        db: Database interactions object used for persistence.
    """

    def __init__(self, db: "DatabaseInteractions") -> None:
        """Initialise the backend.

        Args:
            db: Database interactions object used for persistence.
        """
        self.db = db

    def get_category_tree_with_totals(self) -> List[Category]:
        """
        Return root Category objects with a `totals` attribute (CategoryTotals)
        attached to every node, rolling up all descendant transactions.

        Every category (root or not) gets a fresh :class:`CategoryTotals`
        attached as its ``totals`` attribute. Each booked transaction's
        amount is added directly to its own category's totals (income
        for ``"CRDT"``, expenditure for anything else); those direct
        totals are then rolled up the tree so that every ancestor's
        totals include all of its descendants' activity.

        Returns:
            The top-level (root) :class:`Category` objects, each with
            its subtree fully linked (``children``) and every node's
            ``totals`` populated, including rolled-up descendant sums.
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

    def get_transactions_for_category(self, category_id: int) -> List["Transaction"]:
        """Return only the direct transactions belonging to this category.

        Args:
            category_id: ID of the category to fetch transactions for.
                Descendant categories' transactions are not included.

        Returns:
            A list of matching :class:`Transaction` objects.
        """
        return self.db.get_transactions_by_category(category_id)

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
        if transaction.reference and transaction.reference.startswith(MEMORIAL_PREFIX):
            self.delete_memorial_pair(transaction)
        else:
            self.remove_category(transaction)

    # ── Private helpers ────────────────────────────────────────────────────

    def _roll_up(self, node: Category) -> CategoryTotals:
        """Recursively add children's totals into the parent and return the result.

        Args:
            node: The category subtree root to roll up. Must already
                have a ``totals`` attribute set (as done in
                :meth:`get_category_tree_with_totals`) and its
                ``children`` populated.

        Returns:
            ``node.totals``, after every descendant's totals have been
            merged into it.
        """
        for child in node.children:
            child_totals = self._roll_up(child)
            node.totals.add(child_totals)
        return node.totals