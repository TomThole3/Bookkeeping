# -*- coding: utf-8 -*-
import re

def memorial_prefix(date_str: str) -> str:
    return f"MEM-{date_str.replace('-', '')}-"


def memorial_base_ref(reference: str) -> str:
    """Strip -D / -C suffix to get the shared base reference."""
    return re.sub(r"-[DC]$", "", reference or "")


def next_memorial_index(prefix: str, existing_refs: list[str]) -> int:
    if not existing_refs:
        return 1
    indices = []
    for ref in existing_refs:
        part = ref[len(prefix):]         # e.g. "003-D"
        index_part = part.split("-")[0]  # e.g. "003"
        try:
            indices.append(int(index_part))
        except ValueError:
            pass
    return max(indices, default=0) + 1


def build_memorial_refs(date_str: str, index: int) -> tuple[str, str, str]:
    """Return (base_ref, debit_ref, credit_ref)."""
    base = f"MEM-{date_str.replace('-', '')}-{index:03d}"
    return base, f"{base}-D", f"{base}-C"