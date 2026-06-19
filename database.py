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
                cdt_dbt TEXT,
                date TEXT,
                description TEXT,
                counterparty_name TEXT,
                counterparty_iban TEXT,
                category_id INTEGER REFERENCES categories(id),
                is_split INTEGER DEFAULT 0
            )
            """
        )
        self.conn.commit()

    def _remove_category_recursive(self, category_id):
        cursor = self.conn.execute(
            """
            SELECT id FROM categories WHERE parent_id = ?
            """,
            (category_id,)
        )
        for row in cursor.fetchall():
            self._remove_category_recursive(row[0])

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

    def save_transaction(self, transaction):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO transactions
                (reference, amount, cdt_dbt, date, description,
                 counterparty_name, counterparty_iban, category_id, is_split)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.reference,
                transaction.amount,
                transaction.cdt_dbt,
                transaction.date,
                transaction.description,
                transaction.counterparty_name,
                transaction.counterparty_iban,
                transaction.category_id,
                transaction.is_split,
            ),
        )
        self.conn.commit()

    def update_transaction(self, transaction):
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
        self.conn.commit()
        
    def update_split_parent(self, reference):
        self.conn.execute(
            """
            UPDATE transactions
            SET is_split = 1
            WHERE reference = ?
            """,
            (reference,),
        )
        self.conn.commit()

    def get_uncategorized_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description,
                   counterparty_name, counterparty_iban, category_id
            FROM transactions
            WHERE category_id IS NULL AND is_split = 0
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]

    def get_categorized_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT t.reference, t.amount, t.cdt_dbt, t.date,
                   t.description, t.counterparty_name,
                   t.counterparty_iban, c.name, t.is_split
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.category_id IS NOT NULL
            ORDER BY t.date ASC
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def get_transactions_by_category(self, category_id):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description,
                   counterparty_name, counterparty_iban, category_id, is_split
            FROM transactions
            WHERE category_id = ?
            """,
            (category_id,),
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def get_transactions_with_category_ids(self):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description,
                   counterparty_name, counterparty_iban, category_id, is_split
            FROM transactions
            WHERE category_id IS NOT NULL
            """
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
    
    def remove_category_by_reference(self, reference: str):
        self.conn.execute(
            "UPDATE transactions SET category_id = NULL WHERE reference = ?",
            (reference,)
        )
        self.conn.commit()
    
    def remove_category_by_reference_prefix(self, prefix: str):
        self.conn.execute(
            "UPDATE transactions SET category_id = NULL WHERE reference LIKE ?",
            (f"{prefix}-%",)
        )
        self.conn.commit()
        
    def remove_split_parts(self, prefix: str):
        self.conn.execute(
            "DELETE FROM transactions WHERE reference LIKE ?",
            (f"{prefix}-%",)
        )
        self.conn.execute(
            "UPDATE transactions SET is_split = 0 WHERE reference = ?",
            (prefix,)
        )
        self.conn.commit()

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
        cursor = self.conn.execute(
            """
            INSERT INTO categories (name, parent_id)
            VALUES (?, ?)
            """,
            (category.name, category.parent_id)
        )
        self.conn.commit()
        category.id = cursor.lastrowid
        return category

    def remove_category(self, category_id):
        self._remove_category_recursive(category_id)
        self.conn.commit()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self.conn.close()