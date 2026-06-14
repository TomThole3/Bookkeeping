# -*- coding: utf-8 -*-

class Transaction:
    
    def __init__(self, reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category = None):
        self.reference = reference
        self.amount = amount
        self.cdt_dbt = cdt_dbt
        self.date = date
        self.description = description
        self.origin_name = origin_name
        self.origin_iban = origin_iban
        self.category = category