"""PostPurchaseSatisfactionAgent: safe post-purchase support actions."""

from __future__ import annotations

from .intelligence_agent import ReturnsIntelligenceAgent


class PostPurchaseSatisfactionAgent:
    """Maps a cause to post-purchase actions. Every customer-facing action is a draft
    that needs human approval, and none may hide or obstruct a legitimate return."""

    def __init__(self, intelligence: ReturnsIntelligenceAgent) -> None:
        self._intel = intelligence

    def recommend(self, cause: str) -> list[dict]:
        """Structured post-purchase interventions for a cause."""
        return [{"id": i.id, "name": i.name, "description": i.description, "effort": i.effort,
                 "expected_satisfaction_impact": i.satisfaction_impact or i.expected_impact,
                 "channel": i.channel, "requires_human_approval": True, "status": "DRAFT"}
                for i in self._intel.get_post_purchase(cause)]
