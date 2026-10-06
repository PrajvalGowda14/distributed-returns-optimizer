"""Mock customer-service platform integration.

Creates intervention DRAFTS only. Nothing is ever sent to a customer and
nothing is auto-deployed; every draft requires human approval.
"""

from __future__ import annotations

import uuid

from ..models import SupportDraft

VALID_CAUSES = {"FIT_TOO_SMALL", "FIT_TOO_LARGE", "COMPATIBILITY", "EXPECTATION_MISMATCH",
                "DIMENSION_MISMATCH", "DAMAGED", "SETUP_DIFFICULTY", "DELIVERY_PROBLEM", "OTHER"}


class MockCustomerServicePlatform:
    """In-memory draft queue standing in for Zendesk/Gorgias-style tooling."""

    def __init__(self) -> None:
        self._drafts: list[SupportDraft] = []

    def create_support_intervention_draft(self, cause: str, action: str, channel: str) -> SupportDraft:
        """Create a DRAFT support action. Never contacts a customer."""
        if cause not in VALID_CAUSES:
            raise ValueError(f"unknown cause '{cause}'")
        if not action or not action.strip():
            raise ValueError("action is required")
        if not channel or not channel.strip():
            raise ValueError("channel is required")
        draft = SupportDraft(draft_id=f"DRAFT-{uuid.uuid4().hex[:8].upper()}", cause=cause,
                             action=action.strip(), channel=channel.strip())
        self._drafts.append(draft)
        return draft

    def list_drafts(self) -> list[SupportDraft]:
        return list(self._drafts)
