"""Shared application facade used by both the Streamlit UI and the MCP server.

All business logic lives behind this class; app.py and mcp_server.py only
call it. Every collective result passes ``assert_public_safe`` before it is
returned.
"""

from __future__ import annotations

from pathlib import Path

from . import DATA_DIR, KNOWLEDGE_DIR
from .agents import (PostPurchaseSatisfactionAgent, PrePurchaseInterventionAgent, ReturnPatternAnalysisAgent,
                     ReturnsIntelligenceAgent)
from .audit import PrivacyAuditLog
from .classifier import ReturnCauseClassifier
from .forecasting import ForecastingService
from .integrations import MockCustomerServicePlatform, MockOrderManagementSystem
from .privacy.local_privacy import SIGNAL_SCORE
from .privacy import COLLECTIVE_MIN_RECORDS, LOCAL_MIN_RECORDS, MIN_RETAILERS, PrivacyCoordinator, assert_public_safe
from .retailer_nodes import RetailerNode

RETAILERS: tuple[tuple[str, str, str], ...] = (
    ("RETAILER_A", "retailer_a", "Retailer Node A"),
    ("RETAILER_B", "retailer_b", "Retailer Node B"),
    ("RETAILER_C", "retailer_c", "Retailer Node C"),
)

PRIVACY_RULES: list[dict] = [
    {"rule": "A. Local threshold", "detail": f"A retailer contributes a category-and-cause pattern only with at "
                                             f"least {LOCAL_MIN_RECORDS} local records."},
    {"rule": "B. Retailer diversity", "detail": f"A collective pattern is released only if at least "
                                                f"{MIN_RETAILERS} different retailers contribute."},
    {"rule": "C. Collective threshold", "detail": f"Combined eligible records must be at least "
                                                  f"{COLLECTIVE_MIN_RECORDS}."},
    {"rule": "D. Banded output", "detail": "Exact counts are never shared: signals are Emerging (5-7), Medium "
                                           "(8-14) or High (15+); contributors are Multiple (2) or Broad (3+)."},
]

NEVER_SHARED_FIELDS: list[str] = ["retailer_id", "retailer_token", "local_count", "total_count", "order_id",
                                  "return_id", "customer_comment", "product_name", "exact return rate",
                                  "customer ID", "order value", "customer address"]

LIMITATIONS: list[str] = [
    "Synthetic, fictional data only.",
    "Rule-based keyword classification, not a trained model.",
    "Threshold-based disclosure control, not production differential privacy or secure aggregation.",
    "Forecasts use predefined demonstration assumptions.",
    "OMS and customer-service integrations are mocks.",
    "Retailer nodes are simulated as separate objects in one process.",
]

TOOL_CATALOG: list[dict] = [
    {"name": "analyze_return_patterns", "description": "Approved protected cross-retailer patterns, optionally "
                                                       "filtered by category and signal strength."},
    {"name": "get_pattern_details", "description": "Cause explanation and safe, banded evidence for one approved "
                                                   "pattern."},
    {"name": "recommend_pre_purchase", "description": "Structured pre-purchase interventions for a cause."},
    {"name": "recommend_post_purchase", "description": "Structured post-purchase support actions (drafts, human "
                                                       "approval required)."},
    {"name": "forecast_intervention_impact", "description": "Low / expected / high prevented-return scenario with "
                                                            "an assumption warning."},
    {"name": "get_sanitized_order_context", "description": "Sanitized local demo order context (category, delivery, "
                                                           "exchange, return started)."},
    {"name": "create_support_intervention_draft", "description": "Create a DRAFT support action that requires human "
                                                                 "approval; no customer is contacted."},
    {"name": "get_privacy_audit_summary", "description": "Approved and suppressed privacy decisions without counts "
                                                         "or retailer identities."},
    {"name": "classify_return_text", "description": "Classify ad-hoc return text with the transparent keyword "
                                                    "rules; text is not stored."},
    {"name": "get_category_cause_matrix", "description": "Banded signal score for every category x cause "
                                                         "(0 = not released)."},
    {"name": "prioritize_interventions", "description": "Effort-vs-impact quadrants for a cause's interventions."},
    {"name": "forecast_intervention_portfolio", "description": "Overlap-adjusted forecast for several interventions "
                                                               "on one cause."},
    {"name": "simulate_privacy_policy", "description": "What-if: patterns released under a stricter privacy "
                                                       "policy (nothing is released or logged)."},
    {"name": "search_knowledge_base", "description": "Search interventions by keyword."},
    {"name": "list_support_drafts", "description": "Support drafts created this session (none sent)."},
]


class DataUnavailableError(RuntimeError):
    """Raised when retailer data files are missing."""


class ReturnsOptimizationService:
    """Initializes nodes, coordinator, agents, forecasting and integrations."""

    def __init__(self, data_dir: str | Path = DATA_DIR, knowledge_dir: str | Path = KNOWLEDGE_DIR) -> None:
        classifier = ReturnCauseClassifier(str(Path(knowledge_dir) / "cause_taxonomy.json"))
        self._classifier = classifier
        self._nodes = [RetailerNode(rid, Path(data_dir) / folder, classifier) for rid, folder, _ in RETAILERS]
        self._node_names = [name for _, _, name in RETAILERS]
        for node in self._nodes:
            if node.load_local_data():
                node.classify_local_returns()
        self.data_available = all(n.get_local_health_status()["connected"] for n in self._nodes)

        self.audit = PrivacyAuditLog()
        self.coordinator = PrivacyCoordinator(self._nodes, self.audit)
        self.intelligence = ReturnsIntelligenceAgent(knowledge_dir)
        self.pattern_agent = ReturnPatternAnalysisAgent(self.coordinator, self.intelligence)
        self.pre_purchase_agent = PrePurchaseInterventionAgent(self.intelligence)
        self.post_purchase_agent = PostPurchaseSatisfactionAgent(self.intelligence)
        self.forecasting = ForecastingService(self.intelligence)
        self.oms = MockOrderManagementSystem(self._nodes)
        self.customer_service = MockCustomerServicePlatform()
        if self.data_available:
            self.coordinator.evaluate()

    # ---- helpers -------------------------------------------------------------
    def _require_data(self) -> None:
        if not self.data_available:
            raise DataUnavailableError("Retailer data is missing. Run `python generate_data.py` first.")

    def _validate_cause(self, cause: str) -> str:
        cause = (cause or "").strip().upper()
        if cause not in self.intelligence.known_causes():
            raise ValueError(f"unknown cause '{cause}'. Valid: {self.intelligence.known_causes()}")
        return cause

    # ---- status ----------------------------------------------------------------
    def get_system_status(self) -> dict:
        """Node connectivity and headline (non-identifying) metrics."""
        nodes = [dict(name=name, **node.get_local_health_status())
                 for name, node in zip(self._node_names, self._nodes)]
        status = {"data_available": self.data_available, "nodes": nodes,
                  "interventions_available": self.intelligence.count_interventions(),
                  "approved_patterns": 0, "suppressed_evaluations": 0, "strongest_driver": None}
        if self.data_available:
            summary = self.audit.summary()
            patterns = self.coordinator.patterns
            status.update(approved_patterns=summary["approved"], suppressed_evaluations=summary["suppressed"],
                          strongest_driver=(dict(patterns[0].model_dump(),
                                                 explanation=self.pattern_agent.explain(patterns[0]))
                                            if patterns else None))
        return assert_public_safe(status)

    # ---- pattern analysis --------------------------------------------------------
    def analyze_patterns(self, category: str | None = None, signal: str | None = None) -> list[dict]:
        """Approved protected patterns (only the six public fields)."""
        self._require_data()
        result = [p.model_dump() for p in self.pattern_agent.get_patterns(category=category or None,
                                                                          signal=signal or None)]
        return assert_public_safe(result)

    def approved_categories(self) -> list[str]:
        return sorted({p["category"] for p in self.analyze_patterns()}) if self.data_available else []

    def approved_causes(self, category: str) -> list[str]:
        return [p["cause"] for p in self.analyze_patterns(category=category)] if self.data_available else []

    def get_pattern_details(self, category: str, cause: str) -> dict:
        """Explanation plus banded evidence for one approved pattern."""
        self._require_data()
        cause = self._validate_cause(cause)
        pattern = self.pattern_agent.get_pattern(category, cause)
        if pattern is None:
            return assert_public_safe({"category": category, "cause": cause, "privacy_status": "Not released",
                                       "message": "This pattern is not approved for collective release."})
        return assert_public_safe({
            **pattern.model_dump(), "explanation": self.pattern_agent.explain(pattern),
            "cause_details": self.intelligence.get_cause_description(cause),
            "evidence": {"signal_strength": pattern.signal_strength, "contributor_band": pattern.contributor_band,
                         "classification_confidence": pattern.confidence,
                         "note": "Evidence is banded; exact counts and retailer identities are withheld."}})

    # ---- recommendations -----------------------------------------------------------
    def get_pre_purchase_recommendations(self, cause: str) -> list[dict]:
        return self.pre_purchase_agent.recommend(self._validate_cause(cause))

    def get_post_purchase_recommendations(self, cause: str) -> list[dict]:
        return self.post_purchase_agent.recommend(self._validate_cause(cause))

    def build_intervention_plan(self, category: str, cause: str, intervention_id: str) -> dict:
        """Implementation plan for one intervention against an approved pattern."""
        self._require_data()
        cause = self._validate_cause(cause)
        pattern = self.pattern_agent.get_pattern(category, cause)
        if pattern is None:
            raise ValueError(f"{category} / {cause} is not an approved collective pattern")
        found = self.intelligence.get_intervention(cause, intervention_id)
        if found is None:
            raise ValueError(f"intervention '{intervention_id}' does not apply to {cause}")
        intervention, stage = found
        experiment = self.intelligence.get_experiment(cause)
        return assert_public_safe({
            "category": category, "cause": cause,
            "cause_label": self.intelligence.get_cause_description(cause)["label"],
            "signal_strength": pattern.signal_strength, "contributor_band": pattern.contributor_band,
            "intervention": intervention.name, "intervention_id": intervention.id,
            "stage": "Pre-purchase" if stage == "pre_purchase" else "Post-purchase",
            "description": intervention.description,
            "placement_or_channel": intervention.placement or intervention.channel,
            "effort": intervention.effort, "expected_impact": intervention.expected_impact,
            "success_metric": self.intelligence.get_success_metric(cause),
            "guardrails": self.intelligence.get_risks_and_guardrails(cause)["guardrails"],
            "risks": self.intelligence.get_risks_and_guardrails(cause)["risks"],
            "suggested_experiment": experiment,
            "requires_human_approval": stage == "post_purchase" or intervention.requires_human_approval,
            "status": "DRAFT PLAN"})

    # ---- forecasting -------------------------------------------------------------------
    def forecast_impact(self, cause: str, intervention_id: str, affected_returns: int,
                        implementation_cost: str | None = None, test_duration_days: int | None = None) -> dict:
        """Scenario forecast from user-entered volume and predefined assumptions."""
        return self.forecasting.forecast(self._validate_cause(cause), intervention_id, affected_returns,
                                         implementation_cost, test_duration_days).model_dump()

    # ---- privacy ---------------------------------------------------------------------------
    def get_privacy_audit(self) -> dict:
        """Thresholds, rules and all audit events (no counts, no identities)."""
        events = [e.model_dump() for e in self.audit.events()]
        single = [e for e in events if e["decision"] == "SUPPRESSED"
                  and e["reason"] == "Insufficient retailer diversity"]
        blocked = next((e for e in single if (e["category"], e["cause"]) == ("Beauty", "OTHER")),
                       single[0] if single else None)
        return assert_public_safe({
            "thresholds": {"local_min_records": LOCAL_MIN_RECORDS, "collective_min_records": COLLECTIVE_MIN_RECORDS,
                           "min_retailers": MIN_RETAILERS},
            "rules": PRIVACY_RULES, "summary": self.audit.summary(), "events": events,
            "blocked_single_retailer_example": blocked, "never_shared_fields": NEVER_SHARED_FIELDS,
            "limitations": LIMITATIONS})

    def get_mcp_tool_summary(self) -> list[dict]:
        return list(TOOL_CATALOG)

    # ---- integrations ----------------------------------------------------------------------
    def get_sanitized_order_context(self, example_order_id: str) -> dict:
        """Sanitized local demo order context; only four allowed fields."""
        self._require_data()
        ctx = self.oms.get_sanitized_order_context(example_order_id)
        if ctx is None:
            return {"found": False, "message": "No local demo order matches that reference."}
        return assert_public_safe({"found": True, **ctx.model_dump()})

    def example_order_ids(self) -> list[str]:
        """LOCAL DEMO ONLY: example references for the mock OMS lookup."""
        return [oid for node in self._nodes for oid in node.example_order_ids(2)]

    def create_support_draft(self, cause: str, action: str, channel: str) -> dict:
        """Create a DRAFT support action. No customer is contacted."""
        return self.customer_service.create_support_intervention_draft(
            self._validate_cause(cause), action, channel).model_dump()

    def list_support_drafts(self) -> list[dict]:
        """All drafts created this session (none have been sent)."""
        return [d.model_dump() for d in self.customer_service.list_drafts()]

    # ---- added features ------------------------------------------------------------------------
    def classify_text(self, return_reason: str = "", customer_comment: str = "") -> dict:
        """Classification Lab: classify ad-hoc text locally. The text is neither stored nor shared."""
        if len((return_reason or "") + (customer_comment or "")) > 2000:
            raise ValueError("text is limited to 2000 characters")
        r = self._classifier.classify(return_reason, customer_comment)
        return {"cause": r.cause, "label": self.intelligence.get_cause_description(r.cause)["label"],
                "confidence": r.confidence, "matched_keywords": r.matched_keywords,
                "rule": ("2+ keywords matched" if len(r.matched_keywords) >= 2 else
                         "1 keyword matched" if r.matched_keywords else "no keyword matched (OTHER)"),
                "note": "Processed in memory only; this text is not stored or shared."}

    def category_cause_matrix(self) -> list[dict]:
        """Signal score per approved category x cause (0 = not released). Banded only."""
        self._require_data()
        approved = {(p["category"], p["cause"]): p for p in self.analyze_patterns()}
        categories = sorted({e.category for e in self.audit.events()})
        rows = []
        for cat in categories:
            for cause in self.intelligence.known_causes():
                p = approved.get((cat, cause))
                rows.append({"category": cat, "cause": cause,
                             "signal_score": SIGNAL_SCORE[p["signal_strength"]] if p else 0,
                             "signal_strength": p["signal_strength"] if p else "Not released"})
        return assert_public_safe(rows)

    def intervention_matrix(self, cause: str) -> list[dict]:
        """Effort vs expected impact for every intervention of a cause (for prioritisation)."""
        cause = self._validate_cause(cause)
        rank = {"Low": 1, "Medium": 2, "High": 3}
        rows = []
        for stage, items in (("Pre-purchase", self.intelligence.get_pre_purchase(cause)),
                             ("Post-purchase", self.intelligence.get_post_purchase(cause))):
            for i in items:
                impact, effort = rank[i.expected_impact], rank[i.effort]
                quadrant = ("Quick win" if impact > effort else "Strategic bet" if impact == effort == 3
                            else "Consider" if impact == effort else "Deprioritise")
                rows.append({"id": i.id, "name": i.name, "stage": stage, "effort": i.effort,
                             "expected_impact": i.expected_impact, "effort_score": effort,
                             "impact_score": impact, "priority_score": round(impact / effort, 2),
                             "quadrant": quadrant})
        return sorted(rows, key=lambda r: (-r["priority_score"], -r["impact_score"]))

    def forecast_portfolio(self, cause: str, intervention_ids: list[str], affected_returns: int) -> dict:
        """Combined forecast for several interventions on one cause (overlap-adjusted)."""
        return self.forecasting.forecast_portfolio(self._validate_cause(cause), intervention_ids, affected_returns)

    def simulate_privacy_policy(self, local_min: int, min_retailers: int, collective_min: int) -> dict:
        """What-if: how many patterns would be released under a STRICTER policy? Nothing is released
        or logged by this simulation."""
        self._require_data()
        stricter = self.coordinator.evaluate(local_min, min_retailers, collective_min, dry_run=True)
        current = {(p.category, p.cause) for p in self.coordinator.patterns}
        kept = {(p.category, p.cause) for p in stricter}
        return assert_public_safe({
            "policy": {"local_min_records": local_min, "min_retailers": min_retailers,
                       "collective_min_records": collective_min},
            "approved_under_policy": len(kept), "approved_under_current_policy": len(current),
            "patterns_that_would_be_withheld": [{"category": c, "cause": k} for c, k in sorted(current - kept)],
            "patterns": [p.model_dump() for p in stricter]})

    def search_knowledge(self, query: str) -> list[dict]:
        """Search intervention names and descriptions in the knowledge base."""
        if not query or len(query.strip()) < 2:
            return []
        return self.intelligence.search(query)

    @staticmethod
    def plan_to_markdown(plan: dict) -> str:
        """Render an implementation plan as a Markdown document for export."""
        exp = plan["suggested_experiment"]
        lines = [f"# Implementation plan: {plan['intervention']}", "",
                 f"*Status: {plan['status']} - synthetic prototype data; forecasts are assumptions.*", "",
                 f"- **Category / cause:** {plan['category']} / {plan['cause_label']} (`{plan['cause']}`)",
                 f"- **Protected signal:** {plan['signal_strength']} ({plan['contributor_band']} contributors)",
                 f"- **Stage:** {plan['stage']}",
                 f"- **Placement / channel:** {plan['placement_or_channel']}",
                 f"- **Effort / expected impact:** {plan['effort']} / {plan['expected_impact']}",
                 f"- **Human approval required:** {'Yes' if plan['requires_human_approval'] else 'No'}", "",
                 "## What to build", plan["description"], "",
                 "## Success metric", plan["success_metric"], "",
                 "## Guardrails", *[f"- {g}" for g in plan["guardrails"]], "",
                 "## Risks", *[f"- {r}" for r in plan["risks"]], "",
                 "## Suggested experiment", f"- Design: {exp['design']}",
                 f"- Duration: {exp['duration_days']} days", f"- Primary metric: {exp['primary_metric']}",
                 f"- Guardrail metrics: {', '.join(exp['guardrail_metrics'])}"]
        return "\n".join(lines) + "\n"

    def refresh(self) -> list[dict]:
        """Re-run local classification and a fresh coordinator evaluation."""
        for node in self._nodes:
            if node.load_local_data():
                node.classify_local_returns()
        self.data_available = all(n.get_local_health_status()["connected"] for n in self._nodes)
        if self.data_available:
            self.coordinator.evaluate()
        return self.analyze_patterns() if self.data_available else []
