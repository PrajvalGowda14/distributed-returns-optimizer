"""Privacy thresholds and banding rules (single source of truth).

This prototype uses threshold-based disclosure control, not production
differential privacy or cryptographic secure aggregation.
"""

from __future__ import annotations

from typing import Any

from ..models import RESTRICTED_FIELDS

LOCAL_MIN_RECORDS = 3        # A. a retailer contributes a pattern only with >= 3 local records
MIN_RETAILERS = 2            # B. a collective pattern needs >= 2 contributing retailers
COLLECTIVE_MIN_RECORDS = 5   # C. combined eligible records must be >= 5

SIGNAL_SCORE = {"Emerging": 1, "Medium": 2, "High": 3}


def passes_local_threshold(local_count: int) -> bool:
    """Rule A: does a single retailer have enough records to contribute?"""
    return local_count >= LOCAL_MIN_RECORDS


def signal_band(total_eligible: int) -> str | None:
    """Rule D: band combined eligible records. Returns None below the collective threshold."""
    if total_eligible >= 15:
        return "High"
    if total_eligible >= 8:
        return "Medium"
    if total_eligible >= COLLECTIVE_MIN_RECORDS:
        return "Emerging"
    return None


def contributor_band(n_retailers: int) -> str | None:
    """Rule D: band the number of contributing retailers. None below the diversity threshold."""
    if n_retailers >= 3:
        return "Broad"
    if n_retailers >= MIN_RETAILERS:
        return "Multiple"
    return None


def find_restricted_fields(obj: Any, path: str = "") -> list[str]:
    """Recursively list any restricted keys present in a dict/list structure."""
    found: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in RESTRICTED_FIELDS:
                found.append(f"{path}{k}")
            found += find_restricted_fields(v, f"{path}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            found += find_restricted_fields(v, f"{path}[{i}].")
    return found


def assert_public_safe(obj: Any) -> Any:
    """Raise if a public result contains a restricted field; otherwise return it unchanged."""
    bad = find_restricted_fields(obj)
    if bad:
        raise ValueError(f"restricted fields in public output: {bad}")
    return obj
