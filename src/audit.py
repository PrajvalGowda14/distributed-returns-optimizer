"""In-memory privacy audit log."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import AuditEvent


class PrivacyAuditLog:
    """Records every collective pattern evaluation without counts or identities."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(self, category: str, cause: str, decision: str, reason: str, privacy_rule: str,
               contributor_band: str | None = None) -> AuditEvent:
        """Append one decision. ``contributor_band`` is stored only for approved patterns."""
        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            category=category, cause=cause, decision=decision, reason=reason, privacy_rule=privacy_rule,
            contributor_band=contributor_band if decision == "APPROVED" else None)
        self._events.append(event)
        return event

    def events(self, decision: str | None = None) -> list[AuditEvent]:
        """All events, optionally filtered by decision."""
        return [e for e in self._events if decision is None or e.decision == decision]

    def summary(self) -> dict:
        """Counts of decisions (numbers of evaluations, not of records)."""
        return {"approved": len(self.events("APPROVED")), "suppressed": len(self.events("SUPPRESSED")),
                "total_evaluations": len(self._events)}

    def clear(self) -> None:
        self._events.clear()
