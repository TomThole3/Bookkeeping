# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 18:02:36 2026

@author: tthol
"""

import sqlite3

class Database_Interactions:
    
    def save_unprocessed_transaction(conn, transaction):
        conn.execute(
            """
            INSERT INTO transactions
                (reference, amount, cdt_dbt, date, description, origin_name, origin_iban)
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
        conn.commit()