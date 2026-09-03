"""Data model for the ServiceNow-based blast radius agent.

Deliberately narrow: only the incident table fields the correlation logic
actually uses. Every field maps 1:1 to a standard ServiceNow `incident`
table column -- nothing here assumes a populated CMDB.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _dv(value):
    """ServiceNow reference/choice fields come back as {"display_value":
    ..., "value": ...} when the request includes sysparm_display_value=all.
    Unwrap that; pass plain strings through unchanged."""
    if isinstance(value, dict):
        return value.get("display_value") or value.get("value") or ""
    return value or ""


@dataclass
class Incident:
    sys_id: str
    number: str
    short_description: str
    description: str
    opened_at: str
    location: str
    assignment_group: str
    category: str
    state: str
    priority: str
    cmdb_ci: str
    business_service: str
    work_notes: str
    close_notes: str

    @classmethod
    def from_record(cls, rec: dict) -> "Incident":
        return cls(
            sys_id=_dv(rec.get("sys_id")),
            number=_dv(rec.get("number")),
            short_description=_dv(rec.get("short_description")),
            description=_dv(rec.get("description")),
            opened_at=_dv(rec.get("opened_at")),
            location=_dv(rec.get("location")),
            assignment_group=_dv(rec.get("assignment_group")),
            category=_dv(rec.get("category")),
            state=_dv(rec.get("state")),
            priority=_dv(rec.get("priority")),
            cmdb_ci=_dv(rec.get("cmdb_ci")),
            business_service=_dv(rec.get("business_service")),
            work_notes=_dv(rec.get("work_notes")),
            close_notes=_dv(rec.get("close_notes")),
        )

    @property
    def text(self) -> str:
        """Free text used for symptom/keyword matching."""
        return " ".join(
            part for part in [self.short_description, self.description] if part
        )


@dataclass
class MatchedIncident:
    incident: Incident
    score: float  # 0-1, how strongly it matches the trigger
    reasons: list[str]  # which signals matched, e.g. "same assignment group"
    excluded: bool = False
    exclusion_reason: str | None = None


@dataclass
class BlastRadiusAssessment:
    trigger: Incident
    direct: list[MatchedIncident]  # above the high-confidence threshold, not excluded
    excluded: list[MatchedIncident]  # matched a signal but flagged as false positive
    likely_apps: list[str]
    likely_locations: list[str]
    possible_who: str
    possible_reach: str
    urgency: str
    confidence: int  # 0-100
    cause: str
    summary: str
    sources_checked: list[str]
