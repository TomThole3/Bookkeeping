# -*- coding: utf-8 -*-
"""Backend for the Processing screen.

This module defines :class:`ProcessingWindowBackend`, which handles
importing transactions from CAMT files, booking (and splitting)
transactions, requesting AI category suggestions, saving categorisation
examples, and creating memorial transactions.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from data.camt_parser import CAMTParser
from models.transaction import Transaction
from ai.autocategorizer import AutoCategorizer
from ui.windows.settingswindow import load_settings
from util.memorialhelper import memorial_prefix, next_memorial_index, build_memorial_refs

if TYPE_CHECKING:
    from data.database import DatabaseInteractions
    from ui.windows.processingwindow import ProcessingWindow
    from models.category import Category

# A single row of booking data as collected by ProcessingWindow._book(),
# e.g. {"reference": ..., "side": ..., "date": ..., "counterparty": ...,
# "description": ..., "amount": ..., "category_id": ...}.
BookingRow = Dict[str, Any]

# A row from `categorization_examples`:
# (counterparty, description, amount, side, category_id)
CategorizationExample = Tuple[Optional[str], Optional[str], float, str, int]


class ProcessingWindowBackend:
    """Backend logic for importing, booking, and categorising transactions.

    Attributes:
        parser: Parser used to extract transactions from CAMT.053 files.
        db: Database interactions object used for persistence.
        processingwindow: The owning :class:`ProcessingWindow`, used to
            surface UI feedback (e.g. split-sum error dialogs) back to
            the user.
        settings: Application settings loaded from disk (e.g. whether to
            use few-shot examples for AI categorisation).
    """

    def __init__(self, processingwindow: "ProcessingWindow", db: "DatabaseInteractions") -> None:
        """Initialise the backend.

        Args:
            processingwindow: The owning window, used to call back into
                the UI (e.g. :meth:`ProcessingWindow.show_sum_error`).
            db: Database interactions object used for persistence.
        """
        self.parser: CAMTParser = CAMTParser()
        self.db = db
        self.processingwindow = processingwindow
        self.settings: Dict[str, Any] = load_settings()

    def import_transactions_from_file(self, path: str) -> None:
        """Parse a CAMT.053 file and insert its transactions as unbooked.

        Args:
            path: Filesystem path to the CAMT.053 XML file to import.
        """
        transactions = self.parser.extract_camt_transactions(path)
        for transaction in transactions:
            self.db.book_transaction(transaction)

    def get_unbooked_transactions(self) -> List[Transaction]:
        """Return all transactions that haven't yet been assigned a category.

        Returns:
            A list of unbooked :class:`Transaction` objects.
        """
        return self.db.get_unbooked_transactions()

    def get_categories(self) -> List["Category"]:
        """Return all available categories.

        Returns:
            A flat list of :class:`Category` objects.
        """
        return self.db.get_categories()

    def book_transactions(self, rows: List[BookingRow]) -> None:
        """Persist categorised rows from the processing table.

        Rows without a selected category are discarded. Remaining rows
        are grouped by reference: a reference with a single row is
        booked as a normal categorised transaction update; a reference
        with multiple rows (i.e. split into parts) is validated to
        ensure the split amounts sum back to the original transaction
        total (within a cent), then each part is booked as its own
        transaction with a ``-N`` suffix on its reference and
        ``is_split`` set. If the split amounts don't reconcile, that
        group is skipped and reported via
        :meth:`ProcessingWindow.show_sum_error`.

        Args:
            rows: Booking rows collected from the UI table, each
                expected to contain ``reference``, ``side``, ``date``,
                ``counterparty``, ``description``, ``amount``, and
                ``category_id`` keys.
        """
        rows = [row for row in rows if row.get('category_id') is not None]
    
        transactions: List[Transaction] = []
        for row in rows:
            t = Transaction(
                reference=row["reference"],
                amount=row["amount"],
                side=row.get("side"),
                date=row.get("date"),
                description=row.get("description"),
                counterparty_name=row.get("counterparty"),
                counterparty_iban=None,
            )
            t.category_id = row.get("category_id")
            transactions.append(t)
            
        grouped = self.group_by_reference(transactions)
        for sublist in grouped:
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
                    self.db.book_transaction(sublist[i])
            else:
                self.db.update_transaction(sublist[0])

    def group_by_reference(self, transactions: List[Transaction]) -> List[List[Transaction]]:
        """Group transactions by their shared reference.

        Args:
            transactions: The transactions to group, typically all parts
                (split or not) collected for a single booking operation.

        Returns:
            A list of groups, each a list of transactions sharing the
            same ``reference``. Groups with more than one member
            represent a split transaction.
        """
        groups: Dict[str, List[Transaction]] = defaultdict(list)
    
        for t in transactions:
            groups[t.reference].append(t)
    
        return list(groups.values())

    def validate(self, sublist: List[Transaction], amount: Decimal) -> float:
        """Compute the discrepancy between split amounts and the original total.

        Args:
            sublist: The split parts of a single original transaction.
            amount: The original (pre-split) transaction amount.

        Returns:
            The difference (as a float) between the sum of
            ``sublist``'s amounts and ``amount``. Zero (or very close
            to it) indicates the split is valid.
        """
        total = sum(t.amount for t in sublist)
        return float(Decimal(str(total)) - Decimal(str(amount)))

    def get_ai_suggestions(
        self, transactions: List[Transaction], categories: List["Category"]
    ) -> Dict[str, int]:
        """Request AI-suggested categories for a batch of transactions.

        Args:
            transactions: The transactions to categorise.
            categories: The categories a transaction may be assigned to.

        Returns:
            A dict mapping transaction ``reference`` to suggested
            ``category_id``, as returned by
            :meth:`AutoCategorizer.categorize`. Whether past examples
            are used to guide the model is controlled by the
            ``"use_examples"`` application setting.
        """
        examples = self.get_categorization_examples()
        categorizer = AutoCategorizer(categories, examples=examples, use_examples=self.settings.get("use_examples", True))
        return categorizer.categorize(transactions)

    def save_categorization_example(
        self,
        counterparty: Optional[str],
        description: Optional[str],
        amount: float,
        side: str,
        category_id: int,
    ) -> None:
        """Persist a user-confirmed categorisation as a future few-shot example.

        Args:
            counterparty: Counterparty name of the example transaction.
            description: Description of the example transaction.
            amount: Amount of the example transaction.
            side: ``"CRDT"`` or ``"DBIT"``.
            category_id: The category the user assigned to this
                transaction.
        """
        self.db.save_categorization_example(counterparty, description, amount, side, category_id)

    def get_categorization_examples(self) -> List[CategorizationExample]:
        """Return the most recent categorisation examples for few-shot guidance.

        Returns:
            A list of ``(counterparty, description, amount, side,
            category_id)`` tuples, most recent first.
        """
        return self.db.get_categorization_examples()

    def save_memorial_transaction(
        self,
        date: str,
        description: str,
        amount: float,
        from_category_id: int,
        to_category_id: int,
    ) -> str:
        """Create and persist a new memorial (manual journal) transaction.

        Computes the next available index for the given date, builds
        the debit/credit leg references, and saves both legs to the
        database.

        Args:
            date: Booking date, formatted as ``"YYYY-MM-DD"``.
            description: Shared description for both legs.
            amount: Amount posted to each leg.
            from_category_id: Category charged on the debit leg.
            to_category_id: Category credited on the credit leg.

        Returns:
            The shared base reference for the newly created entry
            (without the ``-D`` / ``-C`` leg suffix).
        """
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