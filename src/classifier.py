"""Deterministic, transparent keyword-based return-cause classifier.

This is NOT a trained machine-learning model. It lower-cases the combined
``return_reason`` and ``customer_comment`` text and counts whole-word keyword
matches per cause from ``knowledge/cause_taxonomy.json``.

Confidence rules:
    0.90 - two or more keywords of the selected cause match
    0.80 - exactly one keyword matches
    0.50 - nothing matches (cause = OTHER)
Ties are broken by the taxonomy's listed priority order.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from . import KNOWLEDGE_DIR
from .models import ClassificationResult

MULTI_MATCH_CONFIDENCE = 0.90
SINGLE_MATCH_CONFIDENCE = 0.80
OTHER_CONFIDENCE = 0.50


@lru_cache(maxsize=4)
def load_taxonomy(path: str | None = None) -> dict:
    """Load the shared cause taxonomy JSON."""
    p = Path(path) if path else KNOWLEDGE_DIR / "cause_taxonomy.json"
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def normalize(text: str) -> str:
    """Lower-case, unify apostrophes and collapse whitespace."""
    text = (text or "").lower().replace("’", "'")
    return re.sub(r"\s+", " ", text).strip()


class ReturnCauseClassifier:
    """Classifies a return into the shared taxonomy using transparent keyword rules."""

    def __init__(self, taxonomy_path: str | None = None) -> None:
        taxonomy = load_taxonomy(taxonomy_path)
        self._rules: list[tuple[str, list[tuple[str, re.Pattern[str]]]]] = [
            (c["code"], [(kw, re.compile(rf"(?<![a-z]){re.escape(kw.lower())}(?![a-z])"))
                         for kw in c["keywords"]])
            for c in taxonomy["causes"]
        ]
        self.cause_codes = [code for code, _ in self._rules]

    def classify(self, return_reason: str = "", customer_comment: str = "") -> ClassificationResult:
        """Classify one return from its reason and comment."""
        text = normalize(f"{return_reason} {customer_comment}")
        best_code, best_hits = "OTHER", []
        for code, patterns in self._rules:
            hits = [kw for kw, pat in patterns if pat.search(text)]
            if len(hits) > len(best_hits):  # strict '>' keeps taxonomy priority on ties
                best_code, best_hits = code, hits
        if not best_hits:
            return ClassificationResult(cause="OTHER", confidence=OTHER_CONFIDENCE)
        confidence = MULTI_MATCH_CONFIDENCE if len(best_hits) >= 2 else SINGLE_MATCH_CONFIDENCE
        return ClassificationResult(cause=best_code, confidence=confidence, matched_keywords=best_hits)
