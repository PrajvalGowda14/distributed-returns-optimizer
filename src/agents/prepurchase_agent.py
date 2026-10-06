"""PrePurchaseInterventionAgent: shopping-experience fixes for an approved cause."""

from __future__ import annotations

from .intelligence_agent import ReturnsIntelligenceAgent


class PrePurchaseInterventionAgent:
    """Maps a cause to pre-purchase interventions with placement and guardrails."""

    def __init__(self, intelligence: ReturnsIntelligenceAgent) -> None:
        self._intel = intelligence

    def recommend(self, cause: str) -> list[dict]:
        """Structured pre-purchase interventions for a cause."""
        guardrails = self._intel.get_risks_and_guardrails(cause)["guardrails"]
        return [{"id": i.id, "name": i.name, "description": i.description, "effort": i.effort,
                 "expected_impact": i.expected_impact, "placement": i.placement, "guardrails": guardrails}
                for i in self._intel.get_pre_purchase(cause)]
