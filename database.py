# -*- coding: utf-8 -*-
import sqlite3
from transaction import Transaction
from category import Category


class DatabaseInteractions:

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self, db_path="transactions.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    def _create_tables(self):
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

    def _unbook_recursive(self, category_id):
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

    def book_transaction(self, transaction):
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

    def update_transaction(self, transaction):
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

    def update_split_parent(self, reference):
        with self.conn:
            self.conn.execute(
                """
                UPDATE transactions
                SET is_split = 1
                WHERE reference = ?
                """,
                (reference,),
            )

    def get_unbooked_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, side, date, description,
                   counterparty_name, counterparty_iban, category_id
            FROM transactions
            WHERE category_id IS NULL AND is_split = 0
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]

    def get_booked_transactions(self):
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

    def get_transactions_by_category(self, category_id):
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

    def get_amount_and_iban(self, reference):
        cursor = self.conn.execute(
            """
            SELECT amount, counterparty_iban
            FROM transactions
            WHERE reference = ?
            """,
            (reference,),
        )
        return cursor.fetchone()

    def unbook_by_reference(self, reference: str):
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET category_id = NULL WHERE reference = ?",
                (reference,)
            )

    def unbook_by_reference_prefix(self, prefix: str):
        with self.conn:
            self.conn.execute(
                "UPDATE transactions SET category_id = NULL WHERE reference LIKE ?",
                (f"{prefix}-%",)
            )

    def unbook_split_parts(self, prefix: str):
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

    def get_categories(self):
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

    def add_category(self, category):
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

    def remove_category(self, category_id):
        self._remove_category_recursive(category_id)

    # ----------------- Memorial transactions --------------------------

    def get_references_with_prefix(self, prefix: str) -> list[str]:
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
        with self.conn:
            self.conn.execute(
                "DELETE FROM transactions WHERE reference = ? OR reference = ?",
                (debit_ref, credit_ref),
            )

    # ------------------------------------------------------------------
    # Categorization Examples
    # ------------------------------------------------------------------

    def save_categorization_example(self, counterparty, description, amount, side, category_id):
        with self.conn:
            self.conn.execute("""
                INSERT INTO categorization_examples (counterparty, description, amount, side, category_id)
                VALUES (?, ?, ?, ?, ?)
            """, (counterparty, description, amount, side, category_id))

    def get_categorization_examples(self, limit=20) -> list:
        cursor = self.conn.execute("""
            SELECT counterparty, description, amount, side, category_id
            FROM categorization_examples
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()