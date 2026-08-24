# -*- coding: utf-8 -*-
"""Parser for CAMT.053 bank statement files.

This module defines :class:`CAMTParser`, which reads an ISO 20022
CAMT.053 XML bank statement and converts its booked ("BOOK" status)
entries into a list of :class:`~transaction.Transaction` objects.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from lxml import etree
from lxml.etree import _Element
from transaction import Transaction

# A raw transaction row as extracted from the XML, before it is turned
# into a Transaction object. Keys are CAMT field names (plus the
# normalised 'Counterparty_Name' / 'Counterparty_IBAN' added later).
RawTransactionRow = Dict[str, Optional[str]]


class CAMTParser:
    """Extracts booked transactions from a CAMT.053 XML statement file.

    Attributes:
        CAMT_NS: XML namespace mapping used for all XPath lookups against
            the CAMT.053 document.
    """

    def __init__(self) -> None:
        """Initialise the parser with the CAMT.053 XML namespace."""
        self.CAMT_NS: Dict[str, str] = {
            'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'
        }  # adjust version if needed

    def _text(self, el: _Element, path: str) -> Optional[str]:
        """Return the text content of a child element, or ``None``.

        Args:
            el: The element to search within.
            path: An XPath expression (using the ``ns`` prefix) locating
                the desired child element relative to ``el``.

        Returns:
            The text content of the matched element, or ``None`` if no
            element matches ``path``.
        """
        found = el.find(path, self.CAMT_NS)
        return found.text if found is not None else None

    def extract_camt_transactions(self, filepath: str) -> List[Transaction]:
        """Parse a CAMT.053 file and return its booked transactions.

        For each ``Ntry`` (statement entry) in the document, one row is
        produced per ``TxDtls`` (transaction detail) it contains, each
        carrying the entry-level fields plus that detail's counterparty
        info. Entries with no ``TxDtls`` still produce a single row with
        empty counterparty fields. Only entries whose status is
        ``"BOOK"`` are kept, and counterparty fields are normalised to a
        single ``Counterparty_Name`` / ``Counterparty_IBAN`` pair before
        being converted into :class:`Transaction` objects.

        Args:
            filepath: Path to the CAMT.053 XML file to parse.

        Returns:
            A list of :class:`Transaction` objects, one per booked
            transaction detail found in the file.
        """
        tree = etree.parse(filepath)
        root = tree.getroot()

        transactions: List[RawTransactionRow] = []

        for ntry in root.findall('.//ns:Ntry', self.CAMT_NS):
            txn: RawTransactionRow = {
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
        transactions = self.normalize_counterparty(transactions)

        return [Transaction.from_dict(entry) for entry in transactions]

    def normalize_counterparty(
        self, transactions: List[RawTransactionRow]
    ) -> List[RawTransactionRow]:
        """Collapse debtor/creditor fields into a single counterparty pair.

        For a credit (``CRDT``) entry, the debtor is the counterparty;
        for a debit (``DBIT``) entry, the creditor is the counterparty.
        This replaces the separate ``Debtor_*`` / ``Creditor_*`` keys
        with unified ``Counterparty_Name`` / ``Counterparty_IBAN`` keys.

        Args:
            transactions: Raw transaction rows, each containing
                ``CdtDbtInd`` plus ``Debtor_Name``, ``Debtor_IBAN``,
                ``Creditor_Name``, and ``Creditor_IBAN`` keys.

        Returns:
            New rows (originals are left untouched) with the debtor/
            creditor fields replaced by ``Counterparty_Name`` and
            ``Counterparty_IBAN``.
        """
        result: List[RawTransactionRow] = []
        for t in transactions:
            new_t = t.copy()
            if new_t['CdtDbtInd'] == 'CRDT':
                new_t['Counterparty_Name'] = new_t.pop('Debtor_Name')
                new_t['Counterparty_IBAN'] = new_t.pop('Debtor_IBAN')
                del new_t['Creditor_Name']
                del new_t['Creditor_IBAN']
            else:  # DBIT
                new_t['Counterparty_Name'] = new_t.pop('Creditor_Name')
                new_t['Counterparty_IBAN'] = new_t.pop('Creditor_IBAN')
                del new_t['Debtor_Name']
                del new_t['Debtor_IBAN']
            result.append(new_t)
        return result