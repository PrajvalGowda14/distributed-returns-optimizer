"""Assumption-based impact forecasting.

prevented returns = affected returns x effectiveness percentage / 100

Percentages come from ``knowledge/interventions.json`` and are scaled by the
intervention's expected-impact level. They are demonstration assumptions,
not validated results.
"""

from __future__ import annotations

from .agents.intelligence_agent import ReturnsIntelligenceAgent
from .models import ForecastResult, PreventedReturns

WARNING = "Prototype forecast based on predefined assumptions. Validate through an experiment before deployment."
COST_LEVELS = ("Low", "Medium", "High")


def impact_band(expected_percent: float) -> str:
    if expected_percent >= 18:
        return "High"
    if expected_percent >= 10:
        return "Medium"
    return "Low"


class ForecastingService:
    """Produces low / expected / high prevented-return scenarios."""

    def __init__(self, intelligence: ReturnsIntelligenceAgent) -> None:
        self._intel = intelligence

    def forecast(self, cause: str, intervention_id: str, affected_returns: int,
                 implementation_cost: str | None = None, test_duration_days: int | None = None) -> ForecastResult:
        """Forecast prevented returns for one intervention.

        Raises ValueError for negative or non-integer volumes, unknown causes or
        interventions, or an invalid cost level.
        """
        if isinstance(affected_returns, bool) or not isinstance(affected_returns, int):
            raise ValueError("affected_returns must be a whole number")
        if affected_returns < 0:
            raise ValueError("affected_returns cannot be negative")
        if cause not in self._intel.known_causes():
            raise ValueError(f"unknown cause '{cause}'")
        found = self._intel.get_intervention(cause, intervention_id)
        if found is None:
            raise ValueError(f"intervention '{intervention_id}' does not apply to {cause}")
        if implementation_cost is not None and implementation_cost not in COST_LEVELS:
            raise ValueError(f"implementation_cost must be one of {COST_LEVELS}")
        if test_duration_days is not None and test_duration_days < 0:
            raise ValueError("test_duration_days cannot be negative")

        intervention, _ = found
        a = self._intel.get_forecast_assumptions(cause)
        pcts = self._percentages(cause, intervention.expected_impact)

        def prevented(pct: float) -> int:
            return max(0, min(affected_returns, round(affected_returns * pct / 100)))

        low, expected, high = (prevented(p) for p in pcts)
        experiment = self._intel.get_experiment(cause)
        duration = test_duration_days if test_duration_days is not None else experiment["duration_days"]
        validation = experiment["design"]
        if test_duration_days is not None and test_duration_days != experiment["duration_days"]:
            validation = f"{test_duration_days}-day randomized A/B test (knowledge base suggests: {validation})"

        return ForecastResult(
            cause=cause, intervention=intervention.name, affected_returns=affected_returns,
            prevented_returns=PreventedReturns(low=low, expected=expected, high=high),
            impact_band=impact_band(pcts[1]), confidence=a["confidence"],
            satisfaction_effect=a["satisfaction_effect"],
            implementation_cost=implementation_cost or a["implementation_cost"],
            recommended_validation=validation, test_duration_days=duration,
            guardrails=self._intel.get_risks_and_guardrails(cause)["guardrails"], warning=WARNING)

    def _percentages(self, cause: str, expected_impact: str) -> list[float]:
        """Low/expected/high effectiveness percentages scaled by impact level."""
        a = self._intel.get_forecast_assumptions(cause)
        scale = self._intel.impact_multipliers.get(expected_impact, 1.0)
        return sorted(p * scale for p in (a["low_percent"], a["expected_percent"], a["high_percent"]))

    def forecast_portfolio(self, cause: str, intervention_ids: list[str], affected_returns: int) -> dict:
        """Forecast a bundle of interventions for one cause.

        Effects overlap on the same returns, so they are combined as
        1 - product(1 - p_i) per scenario rather than summed.
        """
        ids = list(dict.fromkeys(intervention_ids or []))
        if not ids:
            raise ValueError("select at least one intervention")
        if len(ids) > 6:
            raise ValueError("a portfolio may contain at most 6 interventions")
        singles = [self.forecast(cause, i, affected_returns) for i in ids]
        keep = [1.0, 1.0, 1.0]
        for iid in ids:
            intervention, _ = self._intel.get_intervention(cause, iid)
            for k, pct in enumerate(self._percentages(cause, intervention.expected_impact)):
                keep[k] *= 1 - pct / 100
        combined_pct = [round((1 - k) * 100, 1) for k in keep]
        prevented = [max(0, min(affected_returns, round(affected_returns * p / 100))) for p in combined_pct]
        naive = sum(f.prevented_returns.expected for f in singles)
        return {
            "cause": cause, "affected_returns": affected_returns,
            "interventions": [{"id": i, "name": f.intervention, **f.prevented_returns.model_dump()}
                              for i, f in zip(ids, singles)],
            "combined_prevented_returns": dict(zip(("low", "expected", "high"), prevented)),
            "combined_effectiveness_percent": dict(zip(("low", "expected", "high"), combined_pct)),
            "overlap_adjustment": max(0, min(naive, affected_returns) - prevented[1]),
            "method": "Overlapping effects combined as 1 - product(1 - p_i); demonstration assumption.",
            "warning": WARNING,
        }
