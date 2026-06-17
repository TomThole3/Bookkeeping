# -*- coding: utf-8 -*-

import sqlite3
from transaction import Transaction
from category import Category

class DatabaseInteractions:
    
    def __init__(self, db_path="transactions.db"):
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
       
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
                origin_name TEXT,
                origin_iban TEXT,
                category_id INTEGER REFERENCES categories(id),
                is_split INTEGER DEFAULT 0
            )
            """
        )
        self.conn.commit()
       
    def close(self):
        self.conn.close()
    
    def save_transaction(self, transaction):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO transactions
                (reference, amount, cdt_dbt, date, description,
                 origin_name, origin_iban)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.reference,
                transaction.amount,
                transaction.cdt_dbt,
                transaction.date,
                transaction.description,
                transaction.origin_name,
                transaction.origin_iban,
            ),
        )
        self.conn.commit()
        
    def get_uncategorized_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category_id
            FROM transactions
            WHERE category_id IS NULL AND is_split = 0
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def get_transactions_by_category(self, category_id):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category_id
            FROM transactions
            WHERE category_id = ?
            """,
            (category_id,),
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def update_transactions(self, description, category_id, reference):
        self.conn.execute(
            """
            UPDATE transactions
            SET description = ?,
                category_id = ?
            WHERE reference = ?
            """,
            (description, category_id, reference)
        )
        self.conn.commit()

    def _save_split_transaction(self, reference, description, category_id, amount):
        # Find how many split parts already exist to determine the suffix
        cursor = self.conn.execute(
            """
            SELECT COUNT(*) FROM transactions
            WHERE reference LIKE ?
            """,
            (reference + "-%",)
        )
        count = cursor.fetchone()[0]
        split_reference = f"{reference}-{count + 1}"
        self.conn.execute(
            """
            INSERT INTO transactions
                (reference, amount, cdt_dbt, date, description,
                 origin_name, origin_iban, category_id, is_split)
            SELECT ?, ?, cdt_dbt, date, ?, origin_name, origin_iban, ?, 1
            FROM transactions
            WHERE reference = ?
            """,
            (split_reference, amount, description, category_id, reference)
        )

    def remove_splitted_item(self, reference):
        self.conn.execute(
        """
        DELETE FROM transactions
        WHERE reference = ? AND is_split = 0
        """,
        (reference,)
    )

    def get_categories(self):
        cursor = self.conn.execute(
            """
            SELECT id, name, parent_id
            FROM categories
            """
        )
        return [Category(id=row[0], name=row[1], parent_id=row[2]) for row in cursor.fetchall()]
    
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
            UPDATE transactions SET category_id = NULL WHERE category_id = ?
            """,
            (category_id,)
        )
        self.conn.execute(
            """
            DELETE FROM categories WHERE id = ?
            """,
            (category_id,)
        )
        
    def get_categorized_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT t.reference, t.amount, t.cdt_dbt, t.date, t.description,
                   t.origin_name, t.origin_iban, c.name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.category_id IS NOT NULL
            ORDER BY t.date ASC
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]