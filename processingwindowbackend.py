# -*- coding: utf-8 -*-
from camt_parser import CAMTParser
from database import DatabaseInteractions

class ProcessingWindowBackend:

    def __init__(self):
        self.parser = CAMTParser()
        self.db = DatabaseInteractions()

    def import_transactions_from_file(self, path):
        transactions = self.parser.extract_camt_transactions(path)
        for transaction in transactions:
            self.db.save_transaction(transaction)

    def get_uncategorized_transactions(self):
        return self.db.get_uncategorized_transactions()

    def get_categories(self):
        return self.db.get_categories()

    def save_categories(self, transactions):
        self.db.update_transactions(transactions)
        

