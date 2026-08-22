# -*- coding: utf-8 -*-
class Transaction:
    
    def __init__(self, reference, amount, side, date, description, counterparty_name, counterparty_iban, category_id=None, is_split=0):
        self.reference = reference
        self.amount = amount
        self.side = side
        self.date = date
        self.description = description
        self.counterparty_name = counterparty_name
        self.counterparty_iban = counterparty_iban
        self.category_id = category_id
        self.is_split = is_split
        
    @classmethod
    def from_dict(cls, entry):
        return cls(
            reference=entry["NtryRef"],
            amount=float(entry["Amount"]),
            side=entry["CdtDbtInd"],
            date=entry["BookgDt"],
            description=entry["AddtlNtryInf"],
            counterparty_name=entry.get("Counterparty_Name"),
            counterparty_iban=entry.get("Counterparty_IBAN")
        )
    
    def __repr__(self):
        return ", ".join([
            str(self.reference),
        ])