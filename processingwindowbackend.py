# -*- coding: utf-8 -*-
from camt_parser import CAMTParser
from database import DatabaseInteractions
from transaction import Transaction
from collections import defaultdict
from decimal import Decimal
from autocategorizer import AutoCategorizer
from settingswindow import load_settings
from memorialhelper import memorial_prefix, next_memorial_index, build_memorial_refs


class ProcessingWindowBackend:

    def __init__(self, processingwindow):
        self.parser = CAMTParser()
        self.db = DatabaseInteractions()
        self.processingwindow = processingwindow
        self.settings = load_settings()

    def import_transactions_from_file(self, path):
        transactions = self.parser.extract_camt_transactions(path)
        for transaction in transactions:
            self.db.save_transaction(transaction)

    def get_uncategorized_transactions(self):
        return self.db.get_uncategorized_transactions()

    def get_categories(self):
        return self.db.get_categories()

    def save_categories(self, rows):
        rows = [row for row in rows if row.get('category_id') is not None]
    
        transactions = []
        for row in rows:
            t = Transaction(
                reference=row["reference"],
                amount=row["amount"],
                cdt_dbt=row.get("cdt_dbt"),
                date=row.get("date"),
                description=row.get("description"),
                counterparty_name=row.get("counterparty"),
                counterparty_iban=None,
            )
            t.category_id = row.get("category_id")
            transactions.append(t)
            
        transactions = self.group_by_reference(transactions)
        for sublist in transactions:
            if len(sublist) > 1:
                original_amount, iban = self.db.get_amount_and_iban(sublist[0].reference)
                validate = self.validate(sublist, Decimal(str(original_amount)))
                if abs(validate) > Decimal("0.01"):  
                    self.processingwindow.show_sum_error(validate)
                    continue
                self.db.update_split_parent(sublist[0].reference)
                for i in range(len(sublist)):
                    sublist[i].counterparty_iban = iban
                    sublist[i].reference = f'{sublist[i].reference}-{i+1}'
                    sublist[i].is_split = 1
                    self.db.save_transaction(sublist[i])
            else:
                print(f"saving category_id: {sublist[0].category_id!r}, type: {type(sublist[0].category_id)}")
                self.db.update_transaction(sublist[0])
    
    def group_by_reference(self, transactions):
        groups = defaultdict(list)
    
        for t in transactions:
            groups[t.reference].append(t)
    
        return list(groups.values())
    
    def validate(self, sublist, amount):
        total = sum(t.amount for t in sublist)
        return float(Decimal(str(total)) - Decimal(str(amount)))
    
    def get_ai_suggestions(self, transactions: list, categories: list) -> dict:
        examples = self.get_categorization_examples()
        categorizer = AutoCategorizer(categories, examples=examples, use_examples=self.settings.get("use_examples", True))
        return categorizer.categorize(transactions)
    
    def save_categorization_example(self, counterparty, description, amount, cdt_dbt, category_id):
        self.db.save_categorization_example(counterparty, description, amount, cdt_dbt, category_id)
    
    def get_categorization_examples(self) -> list:
        return self.db.get_categorization_examples()
        
    def save_memorial_transaction(self, date, description, amount, from_category_id, to_category_id):
        prefix = memorial_prefix(date)
        existing = self.db.get_references_with_prefix(prefix)
        index = next_memorial_index(prefix, existing)
        base_ref, debit_ref, credit_ref = build_memorial_refs(date, index)
        self.db.save_memorial_transaction(
            date, description, amount,
            debit_ref, credit_ref,
            from_category_id, to_category_id,
        )
        return base_ref
                    
    
        

