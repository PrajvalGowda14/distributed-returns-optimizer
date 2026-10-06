"""Direct tests of the four agent classes (without going through the service layer)."""

import pytest

from src import DATA_DIR
from src.agents import (PostPurchaseSatisfactionAgent, PrePurchaseInterventionAgent, ReturnPatternAnalysisAgent,
                        ReturnsIntelligenceAgent)
from src.audit import PrivacyAuditLog
from src.privacy import PrivacyCoordinator
from src.retailer_nodes import RetailerNode


@pytest.fixture(scope="module")
def intel():
    return ReturnsIntelligenceAgent()


@pytest.fixture(scope="module")
def pattern_agent(intel):
    nodes = [RetailerNode(f"RETAILER_{x}", DATA_DIR / f"retailer_{x.lower()}") for x in "ABC"]
    return ReturnPatternAnalysisAgent(PrivacyCoordinator(nodes, PrivacyAuditLog()), intel)


# ---- A. ReturnPatternAnalysisAgent ----------------------------------------------------

def test_pattern_agent_ranks_by_band(pattern_agent):
    patterns = pattern_agent.get_patterns()
    scores = [pattern_agent.signal_score(p) for p in patterns]
    assert scores == sorted(scores, reverse=True)
    assert (patterns[0].category, patterns[0].cause) == ("Electronics", "COMPATIBILITY")


def test_pattern_agent_filters(pattern_agent):
    assert {p.category for p in pattern_agent.get_patterns(category="Furniture")} == {"Furniture"}
    assert all(p.signal_strength == "Medium" for p in pattern_agent.get_patterns(signal="Medium"))
    assert all(p.cause == "DAMAGED" for p in pattern_agent.get_patterns(cause="DAMAGED"))
    assert pattern_agent.get_pattern("Beauty", "OTHER") is None  # suppressed, never returned


def test_pattern_agent_explanation_has_no_numbers(pattern_agent):
    text = pattern_agent.explain(pattern_agent.get_pattern("Electronics", "COMPATIBILITY"))
    assert text.startswith("Compatibility is a high-strength return driver for Electronics")
    assert "broad group of retailers" in text
    assert not any(ch.isdigit() for ch in text)


# ---- B. PrePurchaseInterventionAgent ----------------------------------------------------

def test_pre_purchase_agent(intel):
    recs = PrePurchaseInterventionAgent(intel).recommend("DIMENSION_MISMATCH")
    assert [r["name"] for r in recs] == ["Prominent dimensions", "Visual size comparison", "Room or context preview"]
    for r in recs:
        assert {"name", "description", "effort", "expected_impact", "placement", "guardrails"} <= set(r)
        assert r["effort"] in ("Low", "Medium", "High") and r["guardrails"]


# ---- C. PostPurchaseSatisfactionAgent ---------------------------------------------------

@pytest.mark.parametrize("cause", ["COMPATIBILITY", "SETUP_DIFFICULTY", "DAMAGED"])
def test_post_purchase_agent_drafts_only(intel, cause):
    recs = PostPurchaseSatisfactionAgent(intel).recommend(cause)
    assert len(recs) == 3
    assert all(r["requires_human_approval"] is True and r["status"] == "DRAFT" for r in recs)


# ---- D. ReturnsIntelligenceAgent -------------------------------------------------------

def test_intelligence_covers_every_cause(intel):
    for cause in intel.known_causes():
        assert intel.get_cause_description(cause)["description"]
        assert intel.get_pre_purchase(cause) and intel.get_post_purchase(cause)
        f = intel.get_forecast_assumptions(cause)
        assert f["low_percent"] <= f["expected_percent"] <= f["high_percent"] and f["disclaimer"]
        assert intel.get_experiment(cause)["design"]
        rg = intel.get_risks_and_guardrails(cause)
        assert rg["risks"] and rg["guardrails"]


def test_intelligence_lookup_and_search(intel):
    found, stage = intel.get_intervention("COMPATIBILITY", "compat_checker")
    assert found.name == "Compatibility checker" and stage == "pre_purchase"
    assert intel.get_intervention("COMPATIBILITY", "nope") is None
    assert any(h["id"] == "offer_replacement" for h in intel.search("replacement"))
    # Unknown cause falls back to the safe OTHER entry.
    assert intel.get_pre_purchase("UNKNOWN")[0].id == "manual_review"
