# -*- coding: utf-8 -*-

class Categorization:

    def __init__(self, conn):
        self.conn = conn

    def add_category(self, name):
        self.conn.execute(
            "INSERT OR IGNORE INTO categories (name) VALUES (?)",
            (name,),
        )
        self.conn.commit()

    def get_all_categories(self):
        cursor = self.conn.execute("SELECT name FROM categories ORDER BY name")
        return [row[0] for row in cursor.fetchall()]

    def delete_category(self, name):
        self.conn.execute("DELETE FROM categories WHERE name = ?", (name,))
        self.conn.commit()