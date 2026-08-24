# -*- coding: utf-8 -*-
"""Category domain model.

This module defines :class:`Category`, representing a (possibly nested)
transaction category. Categories form a tree via ``parent_id`` /
``parent`` / ``children``, which is built lazily from a flat list using
:meth:`Category.build_tree`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class Category:
    """A single transaction category, optionally nested under a parent.

    Instances are typically constructed flat (as loaded from the
    database) with only ``id``, ``name``, and ``parent_id`` set; the
    ``parent`` / ``children`` links are populated afterwards by
    :meth:`build_tree`, and ``totals`` is populated lazily by the
    balance screen's backend.

    Attributes:
        id: Primary key of the category, or ``None`` if not yet
            persisted.
        name: Display name of the category.
        parent_id: Raw foreign key referencing the parent category's
            ``id``, or ``None`` for a top-level category.
        parent: The parent :class:`Category` instance, set by
            :meth:`build_tree`. ``None`` until then (or for top-level
            categories).
        children: List of direct child :class:`Category` instances, set
            by :meth:`build_tree`. Empty until then.
        totals: Aggregated income/expenditure totals for this category,
            lazily attached by ``BalanceWindowBackend``. ``None`` until
            then.
    """

    def __init__(
        self,
        name: str,
        id: Optional[int] = None,
        parent_id: Optional[int] = None,
    ) -> None:
        """Initialise a category.

        Args:
            name: Display name of the category.
            id: Primary key of the category, if already persisted.
                Defaults to ``None`` for a not-yet-saved category.
            parent_id: Foreign key of the parent category, or ``None``
                for a top-level category.
        """
        self.id: Optional[int] = id
        self.name: str = name
        self.parent_id: Optional[int] = parent_id  # raw foreign key from DB
        self.parent: Optional["Category"] = None   # set by build_tree
        self.children: List["Category"] = []        # set by build_tree
        self.totals: Optional[Any] = None  # lazily set by balancewindow

    def full_path(self) -> str:
        """Return this category's full path from the root, e.g. ``"A > B"``.

        Returns:
            The category's name, prefixed by its ancestors' names
            (separated by ``" > "``) if ``parent`` has been set via
            :meth:`build_tree`. Returns just ``name`` for a top-level
            category or one whose tree links haven't been built.
        """
        if self.parent is None:
            return self.name
        return f"{self.parent.full_path()} > {self.name}"

    def __str__(self) -> str:
        """Return the category's display name."""
        return self.name

    @staticmethod
    def build_tree(categories: List["Category"]) -> List["Category"]:
        """Link a flat list of categories into a parent/child tree.

        Populates each category's ``parent`` and ``children`` attributes
        in place based on ``parent_id``.

        Args:
            categories: A flat list of categories (as typically loaded
                from the database), each with ``id`` and ``parent_id``
                set.

        Returns:
            The subset of ``categories`` that are top-level (i.e. have
            ``parent_id is None``) — the roots of the resulting tree.

        Raises:
            KeyError: If a category's ``parent_id`` doesn't match the
                ``id`` of any category in ``categories``.
        """
        lookup: Dict[Optional[int], "Category"] = {c.id: c for c in categories}
        for c in categories:
            if c.parent_id is not None:
                parent = lookup[c.parent_id]
                c.parent = parent
                parent.children.append(c)
        return [c for c in categories if c.parent_id is None]

    @staticmethod
    def build_map(categories: List["Category"]) -> Dict[int, str]:
        """Build a lookup of category ID to category name.

        Args:
            categories: The categories to map.

        Returns:
            A dict mapping each category's ``id`` to its ``name``.
        """
        return {c.id: c.name for c in categories}

    def __eq__(self, other: object) -> bool:
        """Return whether ``other`` is a :class:`Category` with the same ``id``."""
        return isinstance(other, Category) and self.id == other.id

    def __hash__(self) -> int:
        """Return a hash based on the category's ``id``."""
        return hash(self.id)