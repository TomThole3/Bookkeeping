# -*- coding: utf-8 -*-
class Transaction:
    
    def __init__(self, reference, amount, cdt_dbt, date, description, origin_name, origin_iban, category_id=None, is_split=False):
        self.reference = reference
        self.amount = amount
        self.cdt_dbt = cdt_dbt
        self.date = date
        self.description = description
        self.origin_name = origin_name
        self.origin_iban = origin_iban
        self.category_id = category_id
        self.is_split = is_split
        
    @classmethod
    def from_dict(cls, entry):
        return cls(
            reference=entry["NtryRef"],
            amount=float(entry["Amount"]),
            cdt_dbt=entry["CdtDbtInd"],
            date=entry["BookgDt"],
            description=entry["AddtlNtryInf"],
            origin_name=entry.get("Counterparty_Name"),
            origin_iban=entry.get("Counterparty_IBAN")
        )