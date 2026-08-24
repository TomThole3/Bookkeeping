# -*- coding: utf-8 -*-
"""Backend for the category management dialog.

This module defines :class:`CategoryDialogBackend`, a thin wrapper around
:class:`DatabaseInteractions` that mediates category listing, creation,
and removal for :class:`categorydialog.AddCategoryDialog`.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from data.database import DatabaseInteractions
from models.category import Category


class CategoryDialogBackend:
    """Mediates category CRUD operations for the category dialog.

    Attributes:
        db: Database interactions object used to persist and retrieve
            categories.
    """

    def __init__(self) -> None:
        """Initialise the backend with its own database connection."""
        self.db: DatabaseInteractions = DatabaseInteractions()

    def get_categories(self) -> List[Category]:
        """Return all existing categories.

        Returns:
            A flat list of every :class:`Category` currently in the
            database (not yet linked into a tree).
        """
        return self.db.get_categories()

    def add_category(self, name: str, parent_id: Optional[int] = None) -> Optional[Category]:
        """Create and persist a new category.

        Args:
            name: Display name for the new category. Must be unique
                across all categories.
            parent_id: ID of the parent category to nest this one under,
                or ``None`` to create a top-level category.

        Returns:
            The newly created :class:`Category` (with its ``id``
            populated), or ``None`` if a category with that name already
            exists.
        """
        try:
            return self.db.add_category(Category(name=name, parent_id=parent_id))
        except sqlite3.IntegrityError:
            return None

    def remove_category(self, category_id: int) -> None:
        """Remove a category and cascade the removal to its descendants.

        Args:
            category_id: ID of the category to remove. All of its
                subcategories are removed as well, and any transactions
                referencing a removed category are decategorised.
        """
        self.db.remove_category(category_id)