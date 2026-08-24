# -*- coding: utf-8 -*-
"""SQLite persistence layer for the bookkeeping application.

This module defines :class:`DatabaseInteractions`, which owns the SQLite
connection and provides all read/write operations for transactions,
categories, and AI categorisation examples.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from transaction import Transaction
from category import Category

# A row from `categorization_examples`:
# (counterparty, description, amount, side, category_id)
CategorizationExample = Tuple[Optional[str], Optional[str], float, str, int]


class DatabaseInteractions:
    """Owns the SQLite connection and all data access for the app.

    Attributes:
        conn: The open SQLite connection.
    """

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self, db_path: str = "transactions.db") -> None:
        """Open (or create) the database file and ensure tables exist.

        Args:
            db_path: Filesystem path to the SQLite database file.
                Defaults to ``"transactions.db"`` in the current working
                directory.
        """
        self.conn: sqlite3.Connection = sqlite3.connect(db_path)
        self._create_tables()

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        """Create the ``categories``, ``transactions``, and
        ``categorization_examples`` tables if they don't already exist."""
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    parent_id INTEGER REFERENCES categories(id)
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference TEXT UNIQUE,
                    amount REAL,
                    side TEXT,
                    date TEXT,
                    description TEXT,
                    counterparty_name TEXT,
                    counterparty_iban TEXT,
                    category_id INTEGER REFERENCES categories(id),
                    is_split INTEGER DEFAULT 0
                )
                """
            )
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS categorization_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                counterparty TEXT,
                description TEXT,
                amount REAL,
                side TEXT,
                category_id INTEGER
                )
                """
            )

    def _unbook_recursive(self, category_id: int) -> None:
        """Recursively decategorise transactions and delete a category subtree.

        For ``category_id`` and every descendant category (depth-first),
        clears ``category_id`` on any transaction referencing it, then
        deletes the category row itself.

        Args:
            category_id: ID of the category (subtree root) to remove.
        """
        cursor = self.conn.execute(
            """
            SELECT id FROM categories WHERE parent_id = ?
            """,
            (category_id,)
        )
        child_ids = [row[0] for row in cursor.fetchall()]
        for child_id in child_ids:
            self._unbook_recursive(child_id)

        with self.conn:
            self.conn.execute(
                """
                UPDATE transactions
                SET category_id = NULL
                WHERE category_id = ?
                """,
                (category_id,)
            )

            self.conn.execute(
                """
                DELETE FROM categories
                WHERE id = ?
                """,
                (category_id,)
            )

    # ------------------------------------------------------------------
    # Transaction methods
    # ------------------------------------------------------------------

    def book_transaction(self, transaction: Transaction) -> None:
        """Insert a transaction, ignoring it if its reference already exists.

        Args:
            transaction: The transaction to insert. Its ``reference``
                must be unique; if a row with the same reference already
                exists, the insert is silently skipped (``INSERT OR
                IGNORE``).
        """
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO transactions
                    (reference, amount, side, date, description,
                     counterparty_name, counterparty_iban, category_id, is_split)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction.reference,
                    transaction.amount,
                    transaction.side,
                    transaction.date,
                    transaction.description,
                    transaction.counterparty_name,
                    transaction.counterparty_iban,
                    transaction.category_id,
                    transaction.is_split,
                ),
            )

    def update_transaction(self, transaction: Transaction) -> None:
        """Update the description and category of an existing transaction.

        Args:
            transaction: The transaction to update, matched by
                ``reference``. Only ``description`` and ``category_id``
                are written.
        """
        with self.conn:
            self.conn.execute(
                """
                UPDATE transactions
                SET description = ?,
                    category_id = ?
                WHERE reference = ?
                """,
                (
                    transaction.description,
                    transaction.category_id,
                    transaction.reference,
                )
            )

    def update_split_parent(self, reference: str) -> None:
        """Mark a transaction as having been split into multiple parts.

        Args:
            reference: The reference of the original (parent) transaction
                to flag as split.
        """
        with self.conn:
            self.conn.execute(
                """
                UPDATE transactions
                SET is_split = 1
                WHERE reference = ?
                """,
                (reference,),
            )

    def get_unbooked_transactions(self) -> List[Transaction]:
        """Return transactions that have no category and aren't split parents.

        Returns:
            A list of :class:`Transaction` objects with ``category_id
            IS NULL`` and ``is_split = 0``, i.e. transactions still
            awaiting categorisation.
        """
        cursor = self.conn.execute(
            """
            SELECT reference, amount, side, date, description,
                   counterparty_name, counterparty_iban, category_id
            FROM transactions
            WHERE category_id IS NULL AND is_split = 0
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]

    def get_booked_transactions(self) -> List[Transaction]:
        """Return all categorised transactions, ordered by date ascending.

        Returns:
            A list of :class:`Transaction` objects with ``category_id
            IS NOT NULL``, sorted by ``date`` ascending.
        """
        cursor = self.conn.execute(
            """
            SELECT reference, amount, side, date, description,
                   counterparty_name, counterparty_iban, category_id, is_split
            FROM transactions
            WHERE category_id IS NOT NULL
            ORDER BY date ASC
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]

    def get_transactions_by_category(self, category_id: int) -> List[Transaction]:
        """Return the transactions booked directly under a category.

        Args:
            category_id: ID of the category to filter by. Only exact
                matches are returned — descendant categories are not
                included.

        Returns:
            A list of matching :class:`Transaction` objects.
        """
        cursor = self.conn.execute(
            """
            SELECT reference, amount, side, date, description,
                   counterparty_name, counterparty_iban, category_id, is_split
            FROM transactions
            WHERE category_id = ?
            """,
            (category_id,),
        )
        return [Transaction(*row) for row in cursor.fetchall()]

    def get_amount_and_iban(self, reference: str) -> Optional[Tuple[float, Optional[str]]]:
        """Look up a transaction's amount and counterparty IBAN.

        Args:
            reference: The transaction's reference.

        Returns:
            A ``(amount, counterparty_iban)`` tuple, or ``None`` if no
            transaction with that reference exists.
        """
        cursor = self.conn.execute(
            """
            SELECT amount, counterparty_iban
            FROM transactions
            WHERE reference = ?
            """,
            (reference,),
        )
        return cursor.fetchone()

    def unbook_by_reference(self, reference: str) -> None:
        """Clear the category of a single transaction.

        Args:
            reference: Reference of the transaction to decategorise.
        """
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET category_id = NULL WHERE reference = ?",
                (reference,)
            )

    def unbook_by_reference_prefix(self, prefix: str) -> None:
        """Clear the category of every transaction whose reference starts with a prefix.

        Args:
            prefix: Reference prefix to match (as ``"{prefix}-%"`` in
                SQL ``LIKE`` syntax) — used for decategorising all parts
                of a split transaction.
        """
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET category_id = NULL WHERE reference LIKE ?",
                (f"{prefix}-%",)
            )

    def unbook_split_parts(self, prefix: str) -> None:
        """Delete all split parts of a transaction and un-flag the parent.

        Args:
            prefix: Reference of the original (parent) transaction. All
                rows whose reference matches ``"{prefix}-%"`` are
                deleted, and the parent row's ``is_split`` flag is reset
                to 0.
        """
        with self.conn:
            self.conn.execute(
                "DELETE FROM transactions WHERE reference LIKE ?",
                (f"{prefix}-%",)
            )
            self.conn.execute(
                "UPDATE transactions SET is_split = 0 WHERE reference = ?",
                (prefix,)
            )

    # ------------------------------------------------------------------
    # Category methods
    # ------------------------------------------------------------------

    def get_categories(self) -> List[Category]:
        """Return all categories as a flat (unlinked) list.

        Returns:
            A list of :class:`Category` objects built from every row in
            the ``categories`` table. Parent/child links are not set;
            use :meth:`Category.build_tree` to build the tree if needed.
        """
        cursor = self.conn.execute(
            """
            SELECT id, name, parent_id
            FROM categories
            """
        )
        return [
            Category(id=row[0], name=row[1], parent_id=row[2])
            for row in cursor.fetchall()
        ]

    def add_category(self, category: Category) -> Category:
        """Insert a new category and populate its assigned ID.

        Args:
            category: The category to persist. Its ``name`` must be
                unique.

        Returns:
            The same ``category`` instance, with ``id`` set to the
            newly assigned primary key.

        Raises:
            sqlite3.IntegrityError: If a category with the same ``name``
                already exists.
        """
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO categories (name, parent_id)
                VALUES (?, ?)
                """,
                (category.name, category.parent_id)
            )
        category.id = cursor.lastrowid
        return category

    def remove_category(self, category_id: int) -> None:
        """Remove a category (and, recursively, its subtree).

        Args:
            category_id: ID of the category to remove.
        """
        self._unbook_recursive(category_id)

    # ----------------- Memorial transactions --------------------------

    def get_references_with_prefix(self, prefix: str) -> List[str]:
        """Return all transaction references starting with a prefix.

        Args:
            prefix: Prefix to match (as ``"{prefix}%"`` in SQL ``LIKE``
                syntax).

        Returns:
            A list of matching reference strings.
        """
        cursor = self.conn.execute(
            "SELECT reference FROM transactions WHERE reference LIKE ?",
            (f"{prefix}%",),
        )
        return [row[0] for row in cursor.fetchall()]

    def save_memorial_transaction(
        self, date: str, description: str, amount: float,
        debit_ref: str, credit_ref: str,
        from_category_id: int, to_category_id: int,
    ) -> None:
        """Insert both legs of a memorial (manual journal) transaction.

        Args:
            date: Booking date, formatted as ``"YYYY-MM-DD"``.
            description: Shared description for both legs.
            amount: Amount posted to each leg.
            debit_ref: Reference for the debit leg.
            credit_ref: Reference for the credit leg.
            from_category_id: Category charged on the debit leg.
            to_category_id: Category credited on the credit leg.
        """
        with self.conn:
            for ref, side, category_id in [
                (debit_ref,  "DBIT", from_category_id),
                (credit_ref, "CRDT", to_category_id),
            ]:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO transactions
                        (reference, amount, side, date, description,
                         counterparty_name, counterparty_iban, category_id, is_split)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (ref, amount, side, date, description, "Memorial", None, category_id, 0),
                )

    def delete_memorial_pair(self, debit_ref: str, credit_ref: str) -> None:
        """Delete both legs of a memorial transaction.

        Args:
            debit_ref: Reference of the debit leg to delete.
            credit_ref: Reference of the credit leg to delete.
        """
        with self.conn:
            self.conn.execute(
                "DELETE FROM transactions WHERE reference = ? OR reference = ?",
                (debit_ref, credit_ref),
            )

    # ------------------------------------------------------------------
    # Categorization Examples
    # ------------------------------------------------------------------

    def save_categorization_example(
        self,
        counterparty: Optional[str],
        description: Optional[str],
        amount: float,
        side: str,
        category_id: int,
    ) -> None:
        """Store a user-confirmed categorisation as a future few-shot example.

        Args:
            counterparty: Counterparty name of the example transaction.
            description: Description of the example transaction.
            amount: Amount of the example transaction.
            side: ``"CRDT"`` or ``"DBIT"``.
            category_id: The category the user assigned to this
                transaction.
        """
        with self.conn:
            self.conn.execute("""
                INSERT INTO categorization_examples (counterparty, description, amount, side, category_id)
                VALUES (?, ?, ?, ?, ?)
            """, (counterparty, description, amount, side, category_id))

    def get_categorization_examples(self, limit: int = 20) -> List[CategorizationExample]:
        """Return the most recent categorisation examples.

        Args:
            limit: Maximum number of examples to return, most recent
                first. Defaults to 20.

        Returns:
            A list of ``(counterparty, description, amount, side,
            category_id)`` tuples, ordered most-recent first.
        """
        cursor = self.conn.execute("""
            SELECT counterparty, description, amount, side, category_id
            FROM categorization_examples
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()