"""ReturnsIntelligenceAgent: the knowledge base of causes and interventions."""

from __future__ import annotations

import json
from pathlib import Path

from .. import KNOWLEDGE_DIR
from ..models import Intervention

DISCLAIMER = ("All percentages are fictional demonstration assumptions, not proven business results. "
              "Validate through an experiment before deployment.")


class ReturnsIntelligenceAgent:
    """Loads and searches ``knowledge/interventions.json`` and the cause taxonomy."""

    def __init__(self, knowledge_dir: str | Path = KNOWLEDGE_DIR) -> None:
        kdir = Path(knowledge_dir)
        with open(kdir / "interventions.json", encoding="utf-8") as fh:
            self._kb = json.load(fh)
        with open(kdir / "cause_taxonomy.json", encoding="utf-8") as fh:
            self._taxonomy = {c["code"]: c for c in json.load(fh)["causes"]}
        self.impact_multipliers: dict[str, float] = {
            k: v for k, v in self._kb["impact_multipliers"].items() if isinstance(v, (int, float))}

    def _entry(self, cause: str) -> dict:
        return self._kb["causes"].get(cause) or self._kb["causes"]["OTHER"]

    def known_causes(self) -> list[str]:
        return list(self._taxonomy)

    def get_cause_description(self, cause: str) -> dict:
        """Label, description and applicable categories for a cause."""
        tax = self._taxonomy.get(cause, self._taxonomy["OTHER"])
        entry = self._entry(cause)
        return {"cause": tax["code"], "label": tax["label"], "description": entry["description"],
                "taxonomy_definition": tax["description"],
                "applicable_categories": entry["applicable_categories"]}

    def get_pre_purchase(self, cause: str) -> list[Intervention]:
        return [Intervention(**i) for i in self._entry(cause)["pre_purchase"]]

    def get_post_purchase(self, cause: str) -> list[Intervention]:
        return [Intervention(**i) for i in self._entry(cause)["post_purchase"]]

    def get_intervention(self, cause: str, intervention_id: str) -> tuple[Intervention, str] | None:
        """Find an intervention by id and return it with its stage ('pre_purchase'/'post_purchase')."""
        for stage in ("pre_purchase", "post_purchase"):
            for i in self._entry(cause)[stage]:
                if i["id"] == intervention_id:
                    return Intervention(**i), stage
        return None

    def get_forecast_assumptions(self, cause: str) -> dict:
        return dict(self._entry(cause)["forecast"], disclaimer=DISCLAIMER)

    def get_experiment(self, cause: str) -> dict:
        return dict(self._entry(cause)["experiment"])

    def get_success_metric(self, cause: str) -> str:
        return self._entry(cause)["success_metric"]

    def get_risks_and_guardrails(self, cause: str) -> dict:
        entry = self._entry(cause)
        return {"risks": list(entry["risks"]), "guardrails": list(entry["guardrails"])}

    def search(self, query: str) -> list[dict]:
        """Case-insensitive search over intervention names and descriptions."""
        q = query.lower().strip()
        hits = []
        for cause, entry in self._kb["causes"].items():
            for stage in ("pre_purchase", "post_purchase"):
                for i in entry[stage]:
                    if q and (q in i["name"].lower() or q in i["description"].lower()):
                        hits.append({"cause": cause, "stage": stage, "id": i["id"], "name": i["name"]})
        return hits

    def count_interventions(self) -> int:
        return sum(len(e["pre_purchase"]) + len(e["post_purchase"]) for e in self._kb["causes"].values())
