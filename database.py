# -*- coding: utf-8 -*-

import sqlite3
from transaction import Transaction

class DatabaseInteractions:
    
    def __init__(self, db_path="transactions.db"):
       self.conn = sqlite3.connect(db_path)
       self._create_tables()
       
    def _create_tables(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT,
                amount REAL,
                cdt_dbt TEXT,
                date TEXT,
                description TEXT,
                origin_name TEXT,
                origin_iban TEXT,
                category TEXT
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        self.conn.commit()
       
    def close(self):
        self.conn.close()
    
    def save_transaction(self, transaction):
        self.conn.execute(
            """
            INSERT INTO transactions
                (reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category)
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
        