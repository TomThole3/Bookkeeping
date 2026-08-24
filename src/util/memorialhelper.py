# -*- coding: utf-8 -*-
"""Helpers for building and parsing memorial (manual journal) transaction references.

A memorial transaction is a manually entered, two-legged journal entry
that debits one category and credits another for the same amount. Both
legs share a common base reference and are distinguished by a ``-D``
(debit) or ``-C`` (credit) suffix, e.g.::

    MEM-20240115-001-D   (debit leg)
    MEM-20240115-001-C   (credit leg)

This module has no classes; it's a small collection of pure functions
and constants used by :class:`processingwindowbackend.ProcessingWindowBackend`
to generate and parse these references.
"""

from __future__ import annotations

import re
from typing import List, Tuple

#: Suffix appended to the base reference for a memorial entry's debit leg.
DEBIT_SUFFIX: str = "-D"

#: Suffix appended to the base reference for a memorial entry's credit leg.
CREDIT_SUFFIX: str = "-C"

#: Prefix identifying a transaction reference as belonging to a memorial
#: (manual journal) entry, as opposed to an imported bank transaction.
MEMORIAL_PREFIX: str = "MEM-"

#: Compiled pattern matching a trailing debit or credit leg suffix
#: (``-D`` or ``-C``) at the end of a reference string.
MEMORIAL_LEG_RE: re.Pattern[str] = re.compile(
    f"({re.escape(DEBIT_SUFFIX)}|{re.escape(CREDIT_SUFFIX)})$"
)


def memorial_prefix(date_str: str) -> str:
    """Build the reference prefix shared by all memorial entries on a date.

    Used to look up existing memorial references for a given date so a
    new one can be assigned the next available index (see
    :func:`next_memorial_index`).

    Args:
        date_str: The entry's date, formatted as ``"YYYY-MM-DD"``.

    Returns:
        A prefix string shaped as ``"MEM-YYYYMMDD-"`` (dashes in
        ``date_str`` are stripped before insertion).
    """
    return f"{MEMORIAL_PREFIX}{date_str.replace('-', '')}-"


def memorial_base_ref(reference: str) -> str:
    """Strip -D / -C suffix to get the shared base reference.

    Args:
        reference: A full memorial leg reference (e.g. ending in ``-D``
            or ``-C``), or ``None``/empty.

    Returns:
        ``reference`` with any trailing ``-D`` or ``-C`` suffix removed.
        Returns an empty string if ``reference`` is ``None`` or empty.
    """
    return MEMORIAL_LEG_RE.sub("", reference or "")


def next_memorial_index(prefix: str, existing_refs: List[str]) -> int:
    """Determine the next available index for a memorial entry on a given date.

    Args:
        prefix: The date-scoped prefix (as returned by
            :func:`memorial_prefix`) that every existing reference for
            that date starts with.
        existing_refs: Reference strings already used for that date
            (typically fetched from the database via prefix match).
            Each is expected to look like ``"{prefix}{index}-{D|C}"``.

    Returns:
        One greater than the highest numeric index found among
        ``existing_refs`` after stripping ``prefix``, or ``1`` if none
        of them have a valid numeric index.
    """
    indices = [
        int(idx) for ref in existing_refs
        if (idx := ref[len(prefix):].split("-", 1)[0]).isdigit()
    ]
    return max(indices, default=0) + 1


def build_memorial_refs(date_str: str, index: int) -> Tuple[str, str, str]:
    """Build the base, debit-leg, and credit-leg references for a memorial entry.

    Args:
        date_str: The entry's date, formatted as ``"YYYY-MM-DD"``.
        index: The entry's sequence number for that date (see
            :func:`next_memorial_index`), formatted as a zero-padded
            3-digit number.

    Returns:
        A ``(base_ref, debit_ref, credit_ref)`` tuple, e.g.
        ``("MEM-20240115-001", "MEM-20240115-001-D", "MEM-20240115-001-C")``.
    """
    base = f"{MEMORIAL_PREFIX}{date_str.replace('-', '')}-{index:03d}"
    return base, f"{base}{DEBIT_SUFFIX}", f"{base}{CREDIT_SUFFIX}"