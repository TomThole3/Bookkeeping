# -*- coding: utf-8 -*-

import sqlite3
from transaction import Transaction

class Database_Interactions:
    
    def save_transaction(conn, transaction):
        conn.execute(
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
        conn.commit()
        
    def get_uncategorized_transactions(self, conn):
        cursor = conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category
            FROM transactions
            WHERE category IS NULL
            """
        )
        return [Transaction(*row) for row in cursor.fetchall()]
    
    def get_transactions_by_category(conn, category):
        cursor = conn.execute(
            """
            SELECT reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category
            FROM transactions
            WHERE category = ?
            """,
            (category,),
        )
        return [Transaction(*row) for row in cursor.fetchall()]