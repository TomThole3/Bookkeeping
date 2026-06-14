# -*- coding: utf-8 -*-
from lxml import etree

class CAMT_Parser:

    def __init__(self):
        self.CAMT_NS = {'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'}  # adjust version if needed
    
    def _text(self, el, path):
        found = el.find(path, self.CAMT_NS)
        return found.text if found is not None else None
    
    def extract_camt_transactions(self, filepath):
        tree = etree.parse(filepath)
        root = tree.getroot()
    
        transactions = []
    
        for ntry in root.findall('.//ns:Ntry', self.CAMT_NS):
            txn = {
                'NtryRef': self._text(ntry, 'ns:NtryRef'),
                'Amount': self._text(ntry, 'ns:Amt'),
                'CdtDbtInd': self._text(ntry, 'ns:CdtDbtInd'),
                'Status': self._text(ntry, 'ns:Sts'),
                'BookgDt': self._text(ntry, 'ns:BookgDt/ns:Dt'),
                'AddtlNtryInf': self._text(ntry, 'ns:AddtlNtryInf'),
            }
    
            # Counterparty info (debtor or creditor) - can be multiple TxDtls per Ntry
            for tx_dtls in ntry.findall('.//ns:NtryDtls/ns:TxDtls', self.CAMT_NS):
                rltd = tx_dtls.find('ns:RltdPties', self.CAMT_NS)
                row = txn.copy()
    
                if rltd is not None:
                    row['Debtor_Name'] = self._text(rltd, 'ns:Dbtr/ns:Nm')
                    row['Debtor_IBAN'] = self._text(rltd, 'ns:DbtrAcct/ns:Id/ns:IBAN')
                    row['Creditor_Name'] = self._text(rltd, 'ns:Cdtr/ns:Nm')
                    row['Creditor_IBAN'] = self._text(rltd, 'ns:CdtrAcct/ns:Id/ns:IBAN')
                else:
                    row['Debtor_Name'] = None
                    row['Debtor_IBAN'] = None
                    row['Creditor_Name'] = None
                    row['Creditor_IBAN'] = None
    
                transactions.append(row)
    
            # If no TxDtls exist, still add the entry-level info
            if not ntry.findall('.//ns:NtryDtls/ns:TxDtls', self.CAMT_NS):
                txn['Debtor_Name'] = None
                txn['Debtor_IBAN'] = None
                txn['Creditor_Name'] = None
                txn['Creditor_IBAN'] = None
                transactions.append(txn)
        
        transactions = [transaction for transaction in transactions if transaction['Status'] == 'BOOK']
        
        return transactions


if __name__ == '__main__':
    path = input('path ').strip('"')
    xmlparse = CAMT_Parser()
    txns = xmlparse.extract_camt_transactions(path)
    for t in txns:
        print(t)
        print('')