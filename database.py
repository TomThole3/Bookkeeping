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
            CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE,
            amount REAL,
            cdt_dbt TEXT,
            date TEXT,
            description TEXT,
            origin_name TEXT,
            origin_iban TEXT,
            category_id INTEGER REFERENCES categories(id)
                )
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            parent_id INTEGER REFERENCES categories(id)
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
                 origin_name, origin_iban, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction.reference,
                transaction.amount,
                transaction.cdt_dbt,
                transaction.date,
                transaction.description,
                transaction.origin_name,
                transaction.origin_iban,
                transaction.category,
            ),
        )
        self.conn.commit()
        
    def get_uncategorized_transactions(self):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category
            FROM transactions
            WHERE category IS NULL
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def get_transactions_by_category(self, category):
        cursor = self.conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category
            FROM transactions
            WHERE category = ?
            """,
            (category,),
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def update_transactions(self, transactions):
        self.conn.executemany(
            """
            UPDATE transactions
            SET description = ?,
                category = ?
            WHERE reference = ?
            """,
            [(description, category, reference) for reference, description, category in transactions]
        )
        self.conn.commit()
    
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
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category
            FROM transactions
            WHERE category IS NOT NULL AND category != ''
            ORDER BY date ASC
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]
        