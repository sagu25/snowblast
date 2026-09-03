"""Renders a BlastRadiusAssessment as text or JSON.

Same three-ring shape as the reference prototype -- Direct / Likely /
Possible -- but every field traces back to a real ServiceNow record or an
explicit "not populated" note, never an invented value.
"""

from __future__ import annotations

import json

from snow_agent.models import BlastRadiusAssessment


def to_text(a: BlastRadiusAssessment) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("SERVICENOW BLAST RADIUS ASSESSMENT")
    lines.append("=" * 72)

    lines.append("\n[TRIGGER]")
    lines.append(f"  {a.trigger.number} — {a.trigger.short_description}")
    lines.append(f"  Area: {a.trigger.location or 'n/a'}   Group: {a.trigger.assignment_group or 'n/a'}   State: {a.trigger.state or 'n/a'}")

    lines.append("\n[DIRECT] — closely matching incidents")
    if a.direct:
        for m in a.direct:
            lines.append(f"  - {m.incident.number} ({m.score:.2f}) — {m.incident.short_description}")
            lines.append(f"      matched on: {', '.join(m.reasons)}")
    else:
        lines.append("  - none — no other incident matches on group, location, category, or keywords")

    if a.excluded:
        lines.append("\n[EXCLUDED] — matched a signal, flagged as false positive")
        for m in a.excluded:
            lines.append(f"  - {m.incident.number} — {m.exclusion_reason}")

    lines.append("\n[LIKELY] — affected applications / capabilities")
    lines.append(f"  {', '.join(a.likely_apps) if a.likely_apps else 'not populated in ServiceNow (cmdb_ci/business_service empty on matched records)'}")

    lines.append("\n[POSSIBLE] — broader business impact")
    lines.append(f"  Locations: {', '.join(a.likely_locations) if a.likely_locations else 'n/a'}")
    lines.append(f"  Who: {a.possible_who}   Reach: {a.possible_reach}   Urgency: {a.urgency}")

    lines.append(f"\n[CAUSE] {a.cause}")
    lines.append(f"[CONFIDENCE] {a.confidence}%")
    lines.append(f"\n{a.summary}")

    lines.append("\n[EVIDENCE CHECKED]")
    for s in a.sources_checked:
        lines.append(f"  - {s}")

    lines.append(
        "\nNote: advisory only. No incident was closed, re-prioritized, or "
        "declared a major incident. Human review required before any "
        "assessment is posted back to ServiceNow."
    )
    return "\n".join(lines)


def to_json(a: BlastRadiusAssessment) -> str:
    def inc_brief(i):
        return {"number": i.number, "short_description": i.short_description, "location": i.location}

    payload = {
        "trigger": inc_brief(a.trigger),
        "direct": [
            {"incident": inc_brief(m.incident), "score": m.score, "reasons": m.reasons} for m in a.direct
        ],
        "excluded": [
            {"incident": inc_brief(m.incident), "reason": m.exclusion_reason} for m in a.excluded
        ],
        "likely_apps": a.likely_apps,
        "possible": {
            "locations": a.likely_locations,
            "who": a.possible_who,
            "reach": a.possible_reach,
            "urgency": a.urgency,
        },
        "cause": a.cause,
        "confidence": a.confidence,
        "summary": a.summary,
        "sources_checked": a.sources_checked,
    }
    return json.dumps(payload, indent=2)


def to_work_note(a: BlastRadiusAssessment) -> str:
    """What --post-note actually writes back to ServiceNow."""
    return (
        "BLAST RADIUS AI ASSESSMENT\n\n"
        f"Trigger: {a.trigger.number}\n"
        f"Direct cluster: {len(a.direct)} incident(s)"
        + (f" ({len(a.excluded)} excluded as false positive)" if a.excluded else "")
        + "\n"
        f"Likely capabilities: {', '.join(a.likely_apps) or 'not populated in ServiceNow'}\n"
        f"Possible reach: {a.possible_reach} — {a.possible_who}\n"
        f"Confidence: {a.confidence}%\n\n"
        f"{a.summary}\n\n"
        "AI-generated from ServiceNow incident data only. Advisory only — "
        "human validation required. Incident state unchanged."
    )
