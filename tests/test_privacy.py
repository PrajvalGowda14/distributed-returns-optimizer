from src.audit import PrivacyAuditLog
from src.models import LocalPatternSummary
from src.privacy import PrivacyCoordinator, contributor_band, find_restricted_fields, signal_band


class FakeNode:
    """Stands in for a RetailerNode: returns pre-built summaries."""

    def __init__(self, token, rows):
        self.token, self.rows = token, rows

    def get_protected_summary(self):
        out = []
        for category, cause, n in self.rows:
            if n >= 3:
                out.append(LocalPatternSummary(category=category, cause=cause, local_count=n,
                                               average_classification_confidence=0.9,
                                               retailer_token=self.token, threshold_passed=True))
            else:
                out.append(LocalPatternSummary(category=category, cause=cause, retailer_token=self.token,
                                               threshold_passed=False))
        return out


def evaluate(*nodes):
    audit = PrivacyAuditLog()
    patterns = PrivacyCoordinator(list(nodes), audit).evaluate()
    return patterns, {(e.category, e.cause): e for e in audit.events()}


def test_single_retailer_pattern_suppressed():
    patterns, events = evaluate(FakeNode("t1", [("Beauty", "OTHER", 9)]), FakeNode("t2", []))
    assert patterns == []
    assert events[("Beauty", "OTHER")].decision == "SUPPRESSED"
    assert events[("Beauty", "OTHER")].reason == "Insufficient retailer diversity"


def test_too_few_records_suppressed():
    patterns, events = evaluate(FakeNode("t1", [("Sports", "DAMAGED", 2)]),
                                FakeNode("t2", [("Sports", "DAMAGED", 2)]))
    assert patterns == []
    assert events[("Sports", "DAMAGED")].decision == "SUPPRESSED"


def test_two_retailers_five_records_approved():
    patterns, events = evaluate(FakeNode("t1", [("Home", "DAMAGED", 3)]),
                                FakeNode("t2", [("Home", "DAMAGED", 3)]))
    assert len(patterns) == 1
    p = patterns[0]
    assert (p.signal_strength, p.contributor_band, p.privacy_status) == ("Emerging", "Multiple", "Approved")
    assert events[("Home", "DAMAGED")].contributor_band == "Multiple"


def test_ineligible_local_records_do_not_count():
    # 4 + 2 records: the 2 fail the local threshold, so only one retailer is eligible.
    patterns, _ = evaluate(FakeNode("t1", [("Home", "DAMAGED", 4)]), FakeNode("t2", [("Home", "DAMAGED", 2)]))
    assert patterns == []


def test_bands():
    assert [signal_band(n) for n in (4, 5, 7, 8, 14, 15)] == [None, "Emerging", "Emerging", "Medium", "Medium",
                                                            "High"]
    assert [contributor_band(n) for n in (1, 2, 3, 5)] == [None, "Multiple", "Broad", "Broad"]


def test_public_results_exclude_restricted_fields(service):
    patterns = service.analyze_patterns()
    assert patterns
    for p in patterns:
        assert set(p) == {"category", "cause", "signal_strength", "contributor_band", "confidence",
                          "privacy_status"}
        for field in ("retailer_id", "retailer_token", "local_count", "total_count", "customer_comment",
                      "return_rate", "exact_return_rate"):
            assert field not in p
    assert find_restricted_fields(service.get_privacy_audit()) == []


def test_suppressed_audit_events_hide_contributor_band(service):
    for e in service.get_privacy_audit()["events"]:
        if e["decision"] == "SUPPRESSED":
            assert e["contributor_band"] is None


def test_planted_scenarios(service):
    approved = {(p["category"], p["cause"]): p for p in service.analyze_patterns()}
    compat = approved[("Electronics", "COMPATIBILITY")]
    assert (compat["signal_strength"], compat["contributor_band"]) == ("High", "Broad")
    assert compat["confidence"] >= 0.85
    assert ("Footwear", "FIT_TOO_SMALL") in approved
    assert ("Furniture", "DAMAGED") in approved
    assert any(cause == "SETUP_DIFFICULTY" for _, cause in approved)
    events = {(e["category"], e["cause"]): e for e in service.get_privacy_audit()["events"]}
    assert events[("Beauty", "OTHER")]["reason"] == "Insufficient retailer diversity"
    assert events[("Sports", "DAMAGED")]["decision"] == "SUPPRESSED"
    assert events[("Electronics", "DELIVERY_PROBLEM")]["decision"] == "SUPPRESSED"
