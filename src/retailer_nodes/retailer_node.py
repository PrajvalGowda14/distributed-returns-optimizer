"""RetailerNode: runs inside one retailer's environment.

In this single-machine prototype each node is a separate Python object with
its own data directory. In production each node would run inside the
retailer's own infrastructure and only ``get_protected_summary()`` output
would ever cross the network.
"""

from __future__ import annotations

import secrets
from collections import defaultdict
from pathlib import Path

import pandas as pd

from ..classifier import ReturnCauseClassifier
from ..models import ClassificationResult, LocalPatternSummary, SanitizedOrderContext
from ..privacy.local_privacy import passes_local_threshold

REQUIRED_FILES = ("orders.csv", "returns.csv", "support_cases.csv")


class RetailerNode:
    """One retailer's local analytics node. Raw data never leaves this object."""

    def __init__(self, retailer_id: str, data_dir: str | Path,
                 classifier: ReturnCauseClassifier | None = None) -> None:
        self._retailer_id = retailer_id
        self._data_dir = Path(data_dir)
        self._classifier = classifier or ReturnCauseClassifier()
        self._orders: pd.DataFrame | None = None
        self._returns: pd.DataFrame | None = None
        self._support: pd.DataFrame | None = None
        self._classified: list[tuple[str, ClassificationResult]] = []
        self._error: str | None = None

    # ---- local-only operations ------------------------------------------------
    def load_local_data(self) -> bool:
        """Load this retailer's own CSVs. Returns False (and records why) if files are missing."""
        missing = [f for f in REQUIRED_FILES if not (self._data_dir / f).exists()]
        if missing:
            self._error = f"missing {', '.join(missing)} in {self._data_dir.name}"
            return False
        self._orders = pd.read_csv(self._data_dir / "orders.csv")
        self._returns = pd.read_csv(self._data_dir / "returns.csv")
        self._support = pd.read_csv(self._data_dir / "support_cases.csv")
        self._error = None
        return True

    def classify_local_returns(self) -> int:
        """Classify every local return. Comments are processed here and never exported."""
        if self._returns is None and not self.load_local_data():
            return 0
        self._classified = [
            (row.product_category, self._classifier.classify(row.return_reason, row.customer_comment))
            for row in self._returns.itertuples(index=False)
        ]
        return len(self._classified)

    # ---- outputs allowed to leave the node ----------------------------------------
    def get_protected_summary(self) -> list[LocalPatternSummary]:
        """Category-and-cause summaries for the coordinator.

        Patterns that pass the local threshold carry a count and average
        confidence; patterns that fail carry only the key and
        ``threshold_passed=False`` so the coordinator can audit them without
        learning the count. A fresh temporary token is used on every call.
        """
        if not self._classified:
            self.classify_local_returns()
        token = f"tmp-{secrets.token_hex(4)}"
        groups: dict[tuple[str, str], list[float]] = defaultdict(list)
        for category, result in self._classified:
            groups[(category, result.cause)].append(result.confidence)
        out = []
        for (category, cause), confs in sorted(groups.items()):
            if passes_local_threshold(len(confs)):
                out.append(LocalPatternSummary(category=category, cause=cause, local_count=len(confs),
                                               average_classification_confidence=round(sum(confs) / len(confs), 4),
                                               retailer_token=token, threshold_passed=True))
            else:
                out.append(LocalPatternSummary(category=category, cause=cause, retailer_token=token,
                                               threshold_passed=False))
        return out

    def get_sanitized_order_context(self, example_order_id: str) -> SanitizedOrderContext | None:
        """Allowed order fields for a local demo order, or None if this node doesn't own it."""
        if self._orders is None and not self.load_local_data():
            return None
        match = self._orders[self._orders["order_id"] == example_order_id]
        if match.empty:
            return None
        row = match.iloc[0]
        return SanitizedOrderContext(
            product_category=str(row["product_category"]), delivery_status=str(row["delivery_status"]),
            exchange_available=bool(row["exchange_available"]),
            return_started=bool((self._returns["order_id"] == example_order_id).any()))

    def get_local_health_status(self) -> dict:
        """Connection/health info safe to show in the UI (no counts, no identity)."""
        loaded = self._returns is not None
        return {"connected": loaded, "classified": bool(self._classified),
                "status": "Connected" if loaded else "Unavailable",
                "detail": self._error or "Local data loaded and classified"}

    def example_order_ids(self, n: int = 5) -> list[str]:
        """LOCAL DEMO ONLY: a few of this node's own order IDs for the mock OMS lookup."""
        if self._orders is None and not self.load_local_data():
            return []
        return self._orders["order_id"].head(n).tolist()
