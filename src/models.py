"""Pydantic data contracts shared across nodes, privacy, agents, service, UI and MCP.

Public models use ``extra="forbid"`` so a restricted field can never be added
to a released result by accident.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CauseCode = Literal["FIT_TOO_SMALL", "FIT_TOO_LARGE", "COMPATIBILITY", "EXPECTATION_MISMATCH",
                    "DIMENSION_MISMATCH", "DAMAGED", "SETUP_DIFFICULTY", "DELIVERY_PROBLEM", "OTHER"]
SignalStrength = Literal["Emerging", "Medium", "High"]
ContributorBand = Literal["Multiple", "Broad"]
Level = Literal["Low", "Medium", "High"]

# Fields that must never appear in any collective/public output.
RESTRICTED_FIELDS: frozenset[str] = frozenset({
    "retailer_id", "retailer_token", "local_count", "total_count", "order_id", "return_id",
    "customer_comment", "product_name", "return_rate", "exact_return_rate", "customer_id",
    "order_value", "customer_address", "retailer_count",
})


class ClassificationResult(BaseModel):
    """Output of the local keyword classifier."""
    cause: CauseCode
    confidence: float = Field(ge=0, le=1)
    matched_keywords: list[str] = Field(default_factory=list)


class LocalPatternSummary(BaseModel):
    """INTERNAL: one retailer's category-and-cause summary, sent only to the coordinator.

    ``local_count`` is present only when the local threshold passed; it is
    never released by the coordinator.
    """
    category: str
    cause: CauseCode
    local_count: int | None = None
    average_classification_confidence: float | None = None
    retailer_token: str
    threshold_passed: bool


class CollectivePattern(BaseModel):
    """PUBLIC: a protected cross-retailer pattern. Contains no counts and no identities."""
    model_config = ConfigDict(extra="forbid")

    category: str
    cause: CauseCode
    signal_strength: SignalStrength
    contributor_band: ContributorBand
    confidence: float = Field(ge=0, le=1)
    privacy_status: Literal["Approved"] = "Approved"


class AuditEvent(BaseModel):
    """PUBLIC: one privacy decision. No exact counts or retailer identities."""
    model_config = ConfigDict(extra="forbid")

    timestamp: str
    category: str
    cause: CauseCode
    decision: Literal["APPROVED", "SUPPRESSED"]
    reason: str
    privacy_rule: str
    contributor_band: ContributorBand | None = None


class Intervention(BaseModel):
    """A pre- or post-purchase intervention from the knowledge base."""
    id: str
    name: str
    description: str
    effort: Level
    expected_impact: Level
    placement: str | None = None
    channel: str | None = None
    satisfaction_impact: Level | None = None
    requires_human_approval: bool = False


class PreventedReturns(BaseModel):
    low: int = Field(ge=0)
    expected: int = Field(ge=0)
    high: int = Field(ge=0)


class ForecastResult(BaseModel):
    """Scenario projection from user-entered volumes and predefined assumptions."""
    model_config = ConfigDict(extra="forbid")

    cause: CauseCode
    intervention: str
    affected_returns: int = Field(ge=0)
    prevented_returns: PreventedReturns
    impact_band: Level
    confidence: float = Field(ge=0, le=1)
    satisfaction_effect: str
    implementation_cost: Level
    recommended_validation: str
    test_duration_days: int = Field(ge=0)
    guardrails: list[str]
    warning: str


class SanitizedOrderContext(BaseModel):
    """PUBLIC: the only order fields that may leave the mock OMS."""
    model_config = ConfigDict(extra="forbid")

    product_category: str
    delivery_status: str
    exchange_available: bool
    return_started: bool


class SupportDraft(BaseModel):
    """A customer-service action draft. Never sent; always needs human approval."""
    model_config = ConfigDict(extra="forbid")

    draft_id: str
    cause: CauseCode
    action: str
    channel: str
    status: Literal["DRAFT"] = "DRAFT"
    requires_human_approval: Literal[True] = True
    customer_contacted: Literal[False] = False
    message: str = "Draft created. No customer was contacted."
