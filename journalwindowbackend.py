# -*- coding: utf-8 -*-

from database import DatabaseInteractions

class JournalWindowBackend:
    def __init__(self):
        self.db = DatabaseInteractions()

    def get_categorized_transactions(self):
        return self.db.get_categorized_transactions()