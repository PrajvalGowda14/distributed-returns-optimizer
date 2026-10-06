"""MCP server for the Distributed Returns Optimization Agent.

Run (stdio transport):
    python mcp_server.py

Every tool calls the shared service layer; the server never reads the raw
retailer CSVs. MCP standardizes access to tools; privacy is enforced by the
application's thresholding and output controls.
"""

from __future__ import annotations

from functools import lru_cache

from mcp.server.fastmcp import FastMCP

from src.service import ReturnsOptimizationService

mcp = FastMCP(
    "distributed-returns-optimizer",
    instructions=("Protected, cross-retailer return-pattern insights. Outputs are banded and anonymous; "
                  "support actions are drafts that require human approval. Data is synthetic."),
    log_level="WARNING",
)


@lru_cache(maxsize=1)
def service() -> ReturnsOptimizationService:
    return ReturnsOptimizationService()


def _safe(fn, *args, **kwargs):
    """Return a structured error instead of raising, so clients get a readable message."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, RuntimeError) as exc:
        return {"error": str(exc)}


@mcp.tool()
def analyze_return_patterns(category: str = "", signal: str = "") -> list[dict] | dict:
    """Return approved, privacy-protected cross-retailer return patterns.

    Args:
        category: Optional product category filter (e.g. "Electronics").
        signal: Optional signal-strength filter: "Emerging", "Medium" or "High".

    Each pattern contains only category, cause, signal_strength, contributor_band,
    confidence and privacy_status. Exact counts and retailer identities are never returned.
    """
    return _safe(service().analyze_patterns, category or None, signal or None)


@mcp.tool()
def get_pattern_details(category: str, cause: str) -> dict:
    """Explain one approved pattern with its cause description and banded evidence.

    Args:
        category: Product category, e.g. "Electronics".
        cause: Cause code, e.g. "COMPATIBILITY".

    Retailer-level details are never returned.
    """
    return _safe(service().get_pattern_details, category, cause)


@mcp.tool()
def recommend_pre_purchase(cause: str) -> list[dict] | dict:
    """Return structured pre-purchase interventions (name, description, effort, expected
    impact, placement, guardrails) for a return cause such as "COMPATIBILITY"."""
    return _safe(service().get_pre_purchase_recommendations, cause)


@mcp.tool()
def recommend_post_purchase(cause: str) -> list[dict] | dict:
    """Return structured post-purchase support actions for a return cause. All actions are
    drafts that require human approval and must never obstruct a legitimate return."""
    return _safe(service().get_post_purchase_recommendations, cause)


@mcp.tool()
def forecast_intervention_impact(cause: str, intervention_id: str, affected_returns: int,
                                 implementation_cost: str = "", test_duration_days: int = 0) -> dict:
    """Forecast low / expected / high prevented returns for one intervention.

    Args:
        cause: Cause code, e.g. "COMPATIBILITY".
        intervention_id: Intervention id, e.g. "compat_checker".
        affected_returns: User-entered scenario volume (whole number >= 0).
        implementation_cost: Optional override: "Low", "Medium" or "High".
        test_duration_days: Optional experiment length; 0 uses the knowledge-base default.

    Results are prototype projections based on predefined assumptions, not proven outcomes.
    """
    return _safe(service().forecast_impact, cause, intervention_id, affected_returns,
                 implementation_cost or None, test_duration_days or None)


@mcp.tool()
def get_sanitized_order_context(example_order_id: str) -> dict:
    """Return sanitized context for a LOCAL DEMO order: product_category, delivery_status,
    exchange_available and return_started only. No retailer, customer or order identifiers."""
    return _safe(service().get_sanitized_order_context, example_order_id)


@mcp.tool()
def create_support_intervention_draft(cause: str, action: str, channel: str) -> dict:
    """Create a DRAFT customer-support action (status DRAFT, human approval required).
    No customer is contacted and nothing is deployed automatically."""
    return _safe(service().create_support_draft, cause, action, channel)


@mcp.tool()
def get_privacy_audit_summary() -> dict:
    """Return privacy thresholds, rules, and approved/suppressed audit events without exact
    counts or retailer identities."""
    return _safe(service().get_privacy_audit)


@mcp.tool()
def classify_return_text(customer_comment: str, return_reason: str = "") -> dict:
    """Classify ad-hoc return text with the transparent keyword rules (not an ML model).
    Returns cause, confidence and matched keywords. The text is processed in memory and
    is neither stored nor shared."""
    return _safe(service().classify_text, return_reason, customer_comment)


@mcp.tool()
def get_category_cause_matrix() -> list[dict] | dict:
    """Banded signal score (0 = not released, 1 = Emerging, 2 = Medium, 3 = High) for every
    category x cause combination. Contains no counts."""
    return _safe(service().category_cause_matrix)


@mcp.tool()
def prioritize_interventions(cause: str) -> list[dict] | dict:
    """Rank a cause's pre- and post-purchase interventions by expected impact versus effort,
    labelled Quick win / Strategic bet / Consider / Deprioritise."""
    return _safe(service().intervention_matrix, cause)


@mcp.tool()
def forecast_intervention_portfolio(cause: str, intervention_ids: list[str], affected_returns: int) -> dict:
    """Forecast a bundle of up to 6 interventions for one cause. Overlapping effects are combined
    as 1 - product(1 - p_i) instead of being summed. Prototype assumptions only."""
    return _safe(service().forecast_portfolio, cause, intervention_ids, affected_returns)


@mcp.tool()
def simulate_privacy_policy(local_min_records: int = 3, min_retailers: int = 2,
                            collective_min_records: int = 5) -> dict:
    """What-if analysis: which patterns would still be released under a STRICTER policy?
    Thresholds below the policy floor (3 / 2 / 5) are rejected. Nothing is released or logged."""
    return _safe(service().simulate_privacy_policy, local_min_records, min_retailers, collective_min_records)


@mcp.tool()
def search_knowledge_base(query: str) -> list[dict] | dict:
    """Search intervention names and descriptions in the knowledge base (e.g. "exchange")."""
    return _safe(service().search_knowledge, query)


@mcp.tool()
def list_support_drafts() -> list[dict] | dict:
    """List support-intervention drafts created in this server session. None have been sent."""
    return _safe(service().list_support_drafts)


@mcp.resource("returns://taxonomy")
def taxonomy_resource() -> str:
    """The shared return-cause taxonomy with descriptions."""
    intel = service().intelligence
    return "\n".join(f"{c}: {intel.get_cause_description(c)['taxonomy_definition']}" for c in intel.known_causes())


@mcp.resource("returns://privacy-policy")
def privacy_policy_resource() -> str:
    """The privacy rules enforced before any collective release."""
    return "\n".join(f"{r['rule']}: {r['detail']}" for r in service().get_privacy_audit()["rules"])


@mcp.prompt()
def returns_review(category: str = "Electronics") -> str:
    """Guided review of a category's protected return drivers and interventions."""
    return (f"Use analyze_return_patterns with category '{category}'. For the strongest approved cause, call "
            "get_pattern_details, prioritize_interventions and forecast_intervention_portfolio for 100 affected "
            "returns using the top two interventions. Summarise as a short plan. Use only banded signals, never "
            "infer retailer-specific numbers, and state that forecasts are prototype assumptions.")


if __name__ == "__main__":
    mcp.run()
