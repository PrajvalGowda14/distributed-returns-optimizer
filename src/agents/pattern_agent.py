"""ReturnPatternAnalysisAgent: protected cross-retailer return patterns."""

from __future__ import annotations

from ..models import CollectivePattern
from ..privacy.coordinator import PrivacyCoordinator
from ..privacy.local_privacy import SIGNAL_SCORE
from .intelligence_agent import ReturnsIntelligenceAgent

BAND_WORDS = {"Broad": "a broad group of retailers", "Multiple": "multiple retailers"}


class ReturnPatternAnalysisAgent:
    """Reads approved patterns from the coordinator; ranks by bands, never by counts."""

    def __init__(self, coordinator: PrivacyCoordinator, intelligence: ReturnsIntelligenceAgent) -> None:
        self._coordinator = coordinator
        self._intel = intelligence

    def get_patterns(self, category: str | None = None, cause: str | None = None,
                     signal: str | None = None) -> list[CollectivePattern]:
        """Approved patterns, optionally filtered; already ranked by signal, breadth, confidence."""
        return [p for p in self._coordinator.patterns
                if (not category or p.category == category)
                and (not cause or p.cause == cause)
                and (not signal or p.signal_strength == signal)]

    def get_pattern(self, category: str, cause: str) -> CollectivePattern | None:
        found = self.get_patterns(category=category, cause=cause)
        return found[0] if found else None

    def explain(self, pattern: CollectivePattern) -> str:
        """Short human-readable explanation of a protected pattern."""
        label = self._intel.get_cause_description(pattern.cause)["label"]
        pre = self._intel.get_pre_purchase(pattern.cause)
        idea = f" {pre[0].name} could reduce avoidable returns." if pre else ""
        return (f"{label} is a {pattern.signal_strength.lower()}-strength return driver for "
                f"{pattern.category} across {BAND_WORDS[pattern.contributor_band]}.{idea}")

    @staticmethod
    def signal_score(pattern: CollectivePattern) -> int:
        return SIGNAL_SCORE[pattern.signal_strength]
