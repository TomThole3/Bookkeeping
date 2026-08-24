# -*- coding: utf-8 -*-
"""Shared enumerations used across the Muntenman bookkeeping application.

Centralising these avoids magic numbers/strings for screen indices,
table column positions, and chart colours scattered throughout the UI
modules.
"""

from enum import IntEnum, Enum


class Screen(IntEnum):
    """Indices of the top-level screens in the main :class:`QStackedWidget`.

    Matches the order in which screens are added to the stack in
    ``startwindow.py``, so a member can be passed directly to
    ``stack.setCurrentIndex(...)``.

    Attributes:
        MENU: The main menu screen.
        PROCESSING: The transaction processing (import/categorise/book)
            screen.
        JOURNAL: The journal (filterable transaction list) screen.
        BALANCE: The balance (category totals) screen.
        ANALYSIS: The analysis (charts) screen.
        SETTINGS: The settings screen.
    """
    MENU = 0
    PROCESSING = 1
    JOURNAL = 2
    BALANCE = 3
    ANALYSIS = 4
    SETTINGS = 5


class TransactionColumns(IntEnum):
    """Column indices for the transaction tables on the Processing and
    Journal screens.

    Using named members instead of raw integers makes table-building
    code (``table.setItem(row, TransactionColumns.AMOUNT, ...)``)
    self-documenting and keeps column order changes to a single place.

    Attributes:
        REFERENCE: The transaction's unique reference/identifier column.
        SIDE: The credit/debit indicator column (``"CRDT"`` / ``"DBIT"``).
        AMOUNT: The transaction amount column.
        DATE: The booking date column.
        COUNTERPARTY: The counterparty name column.
        DESCRIPTION: The free-text description column.
        CATEGORY: The assigned category column.
        SPLIT: The column hosting the "Split" action button.
    """
    REFERENCE = 0
    SIDE = 1
    AMOUNT = 2
    DATE = 3
    COUNTERPARTY = 4
    DESCRIPTION = 5
    CATEGORY = 6
    SPLIT = 7


class BalanceColumns(IntEnum):
    """Columns for the Balance screen's category drill-down table.

    Kept separate from :class:`TransactionColumns`: this table never
    shows category or split status, so it shouldn't be coupled to
    columns that only exist for other screens.

    Attributes:
        REFERENCE: The transaction's unique reference/identifier column.
        SIDE: The credit/debit indicator column (``"CRDT"`` / ``"DBIT"``).
        AMOUNT: The transaction amount column.
        DATE: The booking date column.
        COUNTERPARTY: The counterparty name column.
        DESCRIPTION: The free-text description column.
    """
    REFERENCE = 0
    SIDE = 1
    AMOUNT = 2
    DATE = 3
    COUNTERPARTY = 4
    DESCRIPTION = 5


class Colours(str, Enum):
    """Named hex colour palette used for chart series and accents.

    Inherits from ``str`` so members can be used directly wherever a
    colour string is expected (e.g. passed straight to matplotlib's
    ``color=`` keyword arguments).

    Attributes:
        COLOUR1: Primary accent colour (purple), e.g. income bars.
        COLOUR2: Secondary accent colour (dark blue), e.g. expenditure
            bars.
        COLOUR3: Tertiary accent colour (magenta), e.g. running balance
            line.
        COLOUR4: Quaternary accent colour (teal), reserved for future use.
        COLOUR5: Quinary accent colour (olive), reserved for future use.
    """
    COLOUR1 = '#800080'
    COLOUR2 = '#314159'
    COLOUR3 = '#DE0DAB'
    COLOUR4 = '#008080'
    COLOUR5 = '#808000'