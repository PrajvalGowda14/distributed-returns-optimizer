"""Tests for the extended features: lab, matrix, prioritisation, portfolio, policy simulator, exports."""

import pytest

from src.privacy import find_restricted_fields


def test_classify_text_explains_rule(service):
    r = service.classify_text("", "Dock does not work with my laptop")
    assert r["cause"] == "COMPATIBILITY" and r["confidence"] == 0.90
    assert set(r["matched_keywords"]) == {"does not work with", "my laptop"}
    assert service.classify_text("", "hello")["cause"] == "OTHER"
    with pytest.raises(ValueError):
        service.classify_text("", "x" * 2001)


def test_matrix_is_banded_and_matches_released_patterns(service):
    rows = service.category_cause_matrix()
    released = {(r["category"], r["cause"]) for r in rows if r["signal_score"] > 0}
    assert released == {(p["category"], p["cause"]) for p in service.analyze_patterns()}
    assert {r["signal_score"] for r in rows} <= {0, 1, 2, 3}
    beauty_other = next(r for r in rows if (r["category"], r["cause"]) == ("Beauty", "OTHER"))
    assert beauty_other["signal_score"] == 0
    assert find_restricted_fields(rows) == []


def test_prioritisation_quadrants(service):
    rows = {r["id"]: r for r in service.intervention_matrix("DIMENSION_MISMATCH")}
    assert rows["prominent_dimensions"]["quadrant"] == "Quick win"
    assert rows["room_context_preview"]["quadrant"] == "Strategic bet"
    assert service.intervention_matrix("DAMAGED")[-1]["quadrant"] == "Deprioritise"


def test_portfolio_combines_with_overlap(service):
    pf = service.forecast_portfolio("COMPATIBILITY", ["compat_checker", "compatible_replacement"], 100)
    c = pf["combined_prevented_returns"]
    singles = [i["expected"] for i in pf["interventions"]]
    assert max(singles) < c["expected"] < sum(singles)          # better than either, less than the sum
    assert c["expected"] == 36                                     # 1 - 0.8 * 0.8
    assert c["low"] <= c["expected"] <= c["high"] <= 100
    assert pf["overlap_adjustment"] == 4 and pf["warning"]


def test_portfolio_validation(service):
    with pytest.raises(ValueError):
        service.forecast_portfolio("COMPATIBILITY", [], 100)
    with pytest.raises(ValueError):
        service.forecast_portfolio("COMPATIBILITY", ["offer_replacement"], 100)
    pf = service.forecast_portfolio("DAMAGED", ["offer_replacement", "offer_replacement"], 10)
    assert len(pf["interventions"]) == 1  # duplicates ignored


def test_policy_simulator_only_stricter_and_side_effect_free(service):
    before = service.get_privacy_audit()["summary"]
    same = service.simulate_privacy_policy(3, 2, 5)
    assert same["approved_under_policy"] == same["approved_under_current_policy"]
    strict = service.simulate_privacy_policy(3, 3, 5)
    assert all(p["contributor_band"] == "Broad" for p in strict["patterns"])
    assert strict["approved_under_policy"] < same["approved_under_policy"]
    assert service.get_privacy_audit()["summary"] == before
    assert len(service.analyze_patterns()) == same["approved_under_current_policy"]
    for loose in ((2, 2, 5), (3, 1, 5), (3, 2, 4)):
        with pytest.raises(ValueError):
            service.simulate_privacy_policy(*loose)


def test_knowledge_search(service):
    names = {h["name"] for h in service.search_knowledge("exchange")}
    assert "Offer one-click exchange" in names
    assert service.search_knowledge("") == [] and service.search_knowledge("zzzz") == []


def test_plan_markdown_export(service):
    md = service.plan_to_markdown(service.build_intervention_plan("Electronics", "COMPATIBILITY", "compat_checker"))
    assert md.startswith("# Implementation plan: Compatibility checker")
    for section in ("## Success metric", "## Guardrails", "## Suggested experiment"):
        assert section in md
    assert "RETAILER_" not in md


def test_draft_queue(service):
    service.create_support_draft("DAMAGED", "Offer replacement", "Customer support queue")
    drafts = service.list_support_drafts()
    assert drafts and all(d["status"] == "DRAFT" and d["customer_contacted"] is False for d in drafts)
