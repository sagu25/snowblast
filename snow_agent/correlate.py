"""Deterministic incident-correlation engine.

Mirrors the 8-step method from the reference prototype (Trigger -> Extract
signals -> Search -> Form direct cluster -> Expand likely impact ->
Expand possible impact -> Challenge false positives -> Prepare analyst
decision), but every score is a plain, auditable formula -- nothing here
is an LLM guess. An LLM is layered on top in narrate.py for language
understanding and chat, never for the clustering math itself.

Scope note (be upfront about what this does NOT do yet): this version
only correlates against the `incident` table. The reference prototype's
"Problem records" and "Change records" evidence sources are a natural v2
extension -- ServiceNowClient would need `search_problems`/`search_changes`
methods and this module would need to weigh that evidence in, but neither
is built here.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta

from snow_agent.models import BlastRadiusAssessment, Incident, MatchedIncident

# Weights sum to 1.0 -- tune these, don't add hidden fudge factors elsewhere.
WEIGHT_ASSIGNMENT_GROUP = 0.25
WEIGHT_LOCATION = 0.20
WEIGHT_CATEGORY = 0.15
WEIGHT_TIME_PROXIMITY = 0.15
WEIGHT_KEYWORD_OVERLAP = 0.25

DIRECT_THRESHOLD = 0.5
TIME_WINDOW_HOURS = 6

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "to", "of", "in", "on",
    "for", "and", "or", "not", "with", "at", "by", "this", "that", "it",
    "be", "has", "have", "had", "after", "before", "from", "as", "we",
}

CONTRADICTION_PHRASES = [
    "unrelated", "duplicate", "no impact", "local issue", "isolated issue",
    "planned", "scheduled maintenance", "false alarm", "user error",
    "resolved independently", "different root cause",
]


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _parse_time(value: str) -> datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _score(trigger: Incident, candidate: Incident) -> tuple[float, list[str]]:
    score = 0.0
    reasons = []

    if trigger.assignment_group and trigger.assignment_group == candidate.assignment_group:
        score += WEIGHT_ASSIGNMENT_GROUP
        reasons.append(f"same assignment group ({trigger.assignment_group})")

    if trigger.location and trigger.location == candidate.location:
        score += WEIGHT_LOCATION
        reasons.append(f"same location ({trigger.location})")

    if trigger.category and trigger.category == candidate.category:
        score += WEIGHT_CATEGORY
        reasons.append(f"same category ({trigger.category})")

    t_time = _parse_time(trigger.opened_at)
    c_time = _parse_time(candidate.opened_at)
    if t_time and c_time:
        hours_apart = abs((t_time - c_time).total_seconds()) / 3600
        if hours_apart <= TIME_WINDOW_HOURS:
            proximity = 1 - (hours_apart / TIME_WINDOW_HOURS)
            score += WEIGHT_TIME_PROXIMITY * proximity
            reasons.append(f"opened {hours_apart:.1f}h apart")

    t_tokens, c_tokens = _tokens(trigger.text), _tokens(candidate.text)
    if t_tokens and c_tokens:
        overlap = len(t_tokens & c_tokens) / len(t_tokens | c_tokens)
        if overlap > 0:
            score += WEIGHT_KEYWORD_OVERLAP * overlap
            reasons.append(f"{overlap:.0%} keyword overlap")

    return round(score, 3), reasons


def _challenge(match: MatchedIncident) -> None:
    """Mutates match in place: look for contradicting evidence in the
    candidate's own notes and exclude it if found."""
    haystack = f"{match.incident.close_notes} {match.incident.work_notes}".lower()
    for phrase in CONTRADICTION_PHRASES:
        if phrase in haystack:
            match.excluded = True
            match.exclusion_reason = f'contains "{phrase}" in notes'
            return


def _most_common(values: list[str]) -> str | None:
    values = [v for v in values if v]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def assess(trigger: Incident, candidates: list[Incident]) -> BlastRadiusAssessment:
    scored = []
    for candidate in candidates:
        score, reasons = _score(trigger, candidate)
        if score <= 0:
            continue
        scored.append(MatchedIncident(incident=candidate, score=score, reasons=reasons))

    scored.sort(key=lambda m: m.score, reverse=True)

    direct = [m for m in scored if m.score >= DIRECT_THRESHOLD]
    for m in direct:
        _challenge(m)

    excluded = [m for m in direct if m.excluded]
    direct = [m for m in direct if not m.excluded]

    all_related = [trigger] + [m.incident for m in direct]
    likely_apps = sorted({i.cmdb_ci or i.business_service for i in all_related if (i.cmdb_ci or i.business_service)})
    likely_locations = sorted({i.location for i in all_related if i.location})

    reach = (
        "single location" if len(likely_locations) <= 1
        else "two locations" if len(likely_locations) == 2
        else f"{len(likely_locations)} locations"
    )
    urgency = _most_common([i.priority for i in all_related]) or trigger.priority or "Unknown"
    cause_category = _most_common([i.category for i in all_related]) or "operational"

    if not direct:
        confidence = 90
        cause = "Likely isolated issue"
        summary = (
            f"{trigger.number} does not match other active or recent incidents on "
            f"assignment group, location, category, or symptom keywords. The blast "
            f"radius is currently limited to this single incident."
        )
    else:
        avg_score = sum(m.score for m in direct) / len(direct)
        confidence = round(min(95, 55 + avg_score * 40))
        if excluded:
            confidence = max(30, confidence - 8 * len(excluded))
        cause = f"Potential {cause_category.lower()} disruption"
        summary = (
            f"{len(direct)} related incident(s) found, correlated by "
            f"{', '.join(sorted({r.split(' (')[0] for m in direct for r in m.reasons}))}. "
            f"Reported across {reach}. "
            + (f"{len(excluded)} candidate match(es) excluded as false positives." if excluded else "")
        )

    return BlastRadiusAssessment(
        trigger=trigger,
        direct=direct,
        excluded=excluded,
        likely_apps=likely_apps,
        likely_locations=likely_locations,
        possible_who=_most_common([i.assignment_group for i in all_related]) or "Unknown",
        possible_reach=reach,
        urgency=urgency,
        confidence=confidence,
        cause=cause,
        summary=summary,
        sources_checked=["Active incidents", "Recently resolved incidents (incident table only)"],
    )
