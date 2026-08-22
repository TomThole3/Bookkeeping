# -*- coding: utf-8 -*-
import re

DEBIT_SUFFIX = "-D"
CREDIT_SUFFIX = "-C"
MEMORIAL_PREFIX = "MEM-"

def memorial_prefix(date_str: str) -> str:
    return f"{MEMORIAL_PREFIX}-{date_str.replace('-', '')}-"

def memorial_base_ref(reference: str) -> str:
    """Strip -D / -C suffix to get the shared base reference."""
    return re.compile(f"({re.escape(DEBIT_SUFFIX)}|{re.escape(CREDIT_SUFFIX)})$").sub("", reference or "")

def next_memorial_index(prefix: str, existing_refs: list[str]) -> int:
    indices = [
        int(idx) for ref in existing_refs
        if (idx := ref[len(prefix):].split("-", 1)[0]).isdigit()
    ]
    return max(indices, default=0) + 1

def build_memorial_refs(date_str: str, index: int) -> tuple[str, str, str]:
    """Return (base_ref, debit_ref, credit_ref)."""
    base = f"{MEMORIAL_PREFIX}-{date_str.replace('-', '')}-{index:03d}"
    return base, f"{base}{DEBIT_SUFFIX}", f"{base}{CREDIT_SUFFIX}"