"""Privacy coordinator: combines retailer summaries into protected collective patterns.

The coordinator never opens a CSV. It only calls ``get_protected_summary()``
on each node. Exact counts are used internally to apply thresholds and pick
bands, then discarded.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from ..audit import PrivacyAuditLog
from ..models import CollectivePattern, LocalPatternSummary
from .local_privacy import (COLLECTIVE_MIN_RECORDS, LOCAL_MIN_RECORDS, MIN_RETAILERS, SIGNAL_SCORE,
                            contributor_band, signal_band)


class SummaryProvider(Protocol):
    def get_protected_summary(self) -> list[LocalPatternSummary]: ...


class PrivacyCoordinator:
    """Applies rules A-D and records every decision in the audit log."""

    def __init__(self, nodes: list[SummaryProvider], audit_log: PrivacyAuditLog) -> None:
        self._nodes = nodes
        self.audit = audit_log
        self._patterns: list[CollectivePattern] = []

    def evaluate(self, local_min: int = LOCAL_MIN_RECORDS, min_retailers: int = MIN_RETAILERS,
                 collective_min: int = COLLECTIVE_MIN_RECORDS, dry_run: bool = False) -> list[CollectivePattern]:
        """Run one evaluation round over fresh node summaries.

        Thresholds may only be made *stricter* than the policy floor. With
        ``dry_run=True`` the result is returned (for policy simulation) without
        touching the audit log or the released pattern set.
        """
        if local_min < LOCAL_MIN_RECORDS or min_retailers < MIN_RETAILERS or collective_min < COLLECTIVE_MIN_RECORDS:
            raise ValueError("privacy thresholds can only be made stricter than the policy floor "
                             f"({LOCAL_MIN_RECORDS}/{MIN_RETAILERS}/{COLLECTIVE_MIN_RECORDS})")
        record = (lambda *a, **k: None) if dry_run else self.audit.record
        if not dry_run:
            self.audit.clear()
        grouped: dict[tuple[str, str], list[LocalPatternSummary]] = defaultdict(list)
        for node in self._nodes:
            for s in node.get_protected_summary():
                grouped[(s.category, s.cause)].append(s)

        approved: list[CollectivePattern] = []
        for (category, cause), summaries in sorted(grouped.items()):
            eligible = [s for s in summaries if s.threshold_passed and s.local_count and s.local_count >= local_min]
            n_retailers = len({s.retailer_token for s in eligible})
            total = sum(s.local_count for s in eligible)

            if not eligible:
                record(category, cause, "SUPPRESSED", "No retailer met the local minimum-record threshold",
                       f"A: local threshold (>= {local_min} records per retailer)")
                continue
            if n_retailers < min_retailers:
                record(category, cause, "SUPPRESSED", "Insufficient retailer diversity",
                       f"B: retailer diversity (>= {min_retailers} retailers)")
                continue
            if total < collective_min:
                record(category, cause, "SUPPRESSED", "Combined eligible records below collective threshold",
                       f"C: collective threshold (>= {collective_min} records)")
                continue

            confidence = sum(s.local_count * s.average_classification_confidence for s in eligible) / total
            band = contributor_band(n_retailers)
            approved.append(CollectivePattern(category=category, cause=cause, signal_strength=signal_band(total),
                                              contributor_band=band, confidence=round(confidence, 2)))
            record(category, cause, "APPROVED", "All collective privacy thresholds passed",
                   "A+B+C passed; D: banded output", contributor_band=band)

        approved.sort(key=lambda p: (-SIGNAL_SCORE[p.signal_strength], p.contributor_band != "Broad",
                                     -p.confidence, p.category, p.cause))
        if not dry_run:
            self._patterns = approved
        return approved

    @property
    def patterns(self) -> list[CollectivePattern]:
        """Most recent approved patterns (evaluates once if needed)."""
        if not self._patterns and not self.audit.events():
            self.evaluate()
        return list(self._patterns)
