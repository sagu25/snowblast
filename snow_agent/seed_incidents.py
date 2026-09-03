"""Creates realistic mock incidents in your ServiceNow instance so there's
live data to run the agent against.

Five scenario clusters, mirroring the diversity of the reference prototype
(a real cluster, an isolated ticket, a fully-excluded false-positive
cluster, a mixed real+false cluster, a second real cluster of a different
flavor) -- but these are just plain incident records with realistic
fields. Nothing pre-declares "these are related": the point is that
snow_agent's own correlation engine (correlate.py) has to discover the
clusters from the fields alone, the same way it would against real data.

Usage:
    python -m snow_agent.seed_incidents
    python -m snow_agent.seed_incidents --dry-run

Needs the same SERVICENOW_* environment variables as snow_main.py.

Note on location/assignment_group: these are reference fields in
ServiceNow -- they only work if a matching record already exists in your
instance. If your PDI doesn't have "Hampton Roads" as a location or
"Network" as an assignment group, creation of that field will fail; this
script catches that and retries without location/assignment_group rather
than aborting, so the demo still runs (correlation just leans more on
category/timing/keywords for that record). Edit the LOCATIONS/GROUPS
constants below to match what's actually in your instance for the full
effect.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from snow_agent.client import ServiceNowClient, ServiceNowError, NoCredentialsConfigured

NOW = datetime.utcnow()


def _at(minutes_ago: int) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")


# Edit these to match records that actually exist in your instance.
LOCATIONS = {
    "hampton_roads": "Hampton Roads",
    "richmond": "Richmond Office",
    "virginia": "Virginia",
    "central_virginia": "Central Virginia",
}
GROUPS = {
    "network": "Network",
    "service_desk": "Service Desk",
    "database": "Database",
    "hardware": "Hardware",
}

SCENARIOS = [
    {
        "name": "Storm cluster (real)",
        "note": "3 incidents sharing location/category/timing -- should form a direct cluster",
        "incidents": [
            {
                "short_description": "Multiple outage-related contacts after severe weather",
                "description": "Customers across the region are reporting service outages following severe storm activity overnight.",
                "location": LOCATIONS["hampton_roads"], "assignment_group": GROUPS["network"],
                "category": "network", "priority": "1", "minutes_ago": 5,
            },
            {
                "short_description": "Outage status updates delayed for operations users",
                "description": "Operations dashboards are not reflecting current outage status in the affected region.",
                "location": LOCATIONS["hampton_roads"], "assignment_group": GROUPS["network"],
                "category": "network", "priority": "2", "minutes_ago": 45,
            },
            {
                "short_description": "Customer portal showing incorrect outage map",
                "description": "The customer-facing outage map is not updating to match reported outages in the region.",
                "location": LOCATIONS["hampton_roads"], "assignment_group": GROUPS["service_desk"],
                "category": "network", "priority": "3", "minutes_ago": 90,
            },
        ],
    },
    {
        "name": "Isolated incident",
        "note": "No siblings seeded nearby -- should report as isolated",
        "incidents": [
            {
                "short_description": "Single user cannot open expense reporting tool",
                "description": "One employee reports the expense reporting tool fails to load; no other users affected.",
                "location": LOCATIONS["richmond"], "assignment_group": GROUPS["service_desk"],
                "category": "software", "priority": "4", "minutes_ago": 2,
            },
        ],
    },
    {
        "name": "False-positive cluster",
        "note": "Both candidates share surface signals but their notes contradict -- should be fully excluded",
        "incidents": [
            {
                "short_description": "Multiple outage keywords detected in customer cases",
                "description": "Several recent customer cases reference outage-related terms in the same area.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["service_desk"],
                "category": "network", "priority": "3", "minutes_ago": 10,
            },
            {
                "short_description": "Customer billing question mentions outage",
                "description": "Customer asked whether a past outage affected their bill.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["service_desk"],
                "category": "network", "priority": "4", "minutes_ago": 30,
                "state": "Resolved",
                "close_notes": "Resolved independently -- this was a billing question, unrelated to any outage.",
            },
            {
                "short_description": "Local device restart needed",
                "description": "A single device required a restart after intermittent connectivity.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["service_desk"],
                "category": "network", "priority": "4", "minutes_ago": 15,
                "state": "Resolved",
                "close_notes": "Local issue, planned reboot resolved it.",
            },
        ],
    },
    {
        "name": "Payment/portal disruption (real)",
        "note": "A second real cluster, different flavor, spanning two assignment groups",
        "incidents": [
            {
                "short_description": "Customer payments failing intermittently",
                "description": "Customers report payment attempts failing on the customer portal and mobile app.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["database"],
                "category": "software", "priority": "1", "minutes_ago": 8,
            },
            {
                "short_description": "Customer portal login timeouts reported",
                "description": "Users are experiencing timeouts when logging into the customer portal.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["database"],
                "category": "software", "priority": "2", "minutes_ago": 25,
            },
            {
                "short_description": "Increase in customer contact volume after payment errors",
                "description": "Contact center is seeing higher call volume following reports of payment errors.",
                "location": LOCATIONS["virginia"], "assignment_group": GROUPS["service_desk"],
                "category": "software", "priority": "3", "minutes_ago": 50,
            },
        ],
    },
    {
        "name": "Mixed cluster (real + false positive)",
        "note": "One real match, one that gets excluded -- confidence should land in between",
        "incidents": [
            {
                "short_description": "Field crew mobile sync errors reported by multiple crews",
                "description": "Several field crews report the mobile work-order app is failing to sync.",
                "location": LOCATIONS["central_virginia"], "assignment_group": GROUPS["hardware"],
                "category": "hardware", "priority": "2", "minutes_ago": 6,
            },
            {
                "short_description": "Crew dispatch delayed due to mobile app errors",
                "description": "Dispatch is delayed because the mobile app is not syncing new work orders.",
                "location": LOCATIONS["central_virginia"], "assignment_group": GROUPS["hardware"],
                "category": "hardware", "priority": "2", "minutes_ago": 20,
            },
            {
                "short_description": "Mobile device replacement requested",
                "description": "A single field device needs replacement after physical damage.",
                "location": LOCATIONS["central_virginia"], "assignment_group": GROUPS["hardware"],
                "category": "hardware", "priority": "4", "minutes_ago": 12,
                "state": "Resolved",
                "close_notes": "Unrelated -- hardware replacement request, not an app or sync issue.",
            },
        ],
    },
]


def build_fields(inc: dict) -> dict:
    fields = {
        "short_description": inc["short_description"],
        "description": inc["description"],
        "location": inc["location"],
        "assignment_group": inc["assignment_group"],
        "category": inc["category"],
        "priority": inc["priority"],
        "opened_at": _at(inc["minutes_ago"]),
    }
    if "state" in inc:
        fields["state"] = inc["state"]
    if "close_notes" in inc:
        fields["close_notes"] = inc["close_notes"]
    return fields


def create_with_fallback(client: ServiceNowClient, fields: dict) -> dict:
    try:
        return client.create_incident(fields)
    except ServiceNowError as exc:
        stripped = {k: v for k, v in fields.items() if k not in ("location", "assignment_group")}
        print(f"    warning: create failed ({exc}); retrying without location/assignment_group")
        return client.create_incident(stripped)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print what would be created, don't call ServiceNow")
    args = parser.parse_args(argv)

    if args.dry_run:
        for scenario in SCENARIOS:
            print(f"\n{scenario['name']} -- {scenario['note']}")
            for inc in scenario["incidents"]:
                print(f"  - [{_at(inc['minutes_ago'])}] {inc['short_description']}")
        print("\n(dry run -- nothing created)")
        return 0

    try:
        client = ServiceNowClient()
    except NoCredentialsConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("Creating mock incidents...\n")
    for scenario in SCENARIOS:
        print(f"{scenario['name']} -- {scenario['note']}")
        trigger_number = None
        for i, inc in enumerate(scenario["incidents"]):
            fields = build_fields(inc)
            record = create_with_fallback(client, fields)
            number = record.get("number", "?")
            if i == 0:
                trigger_number = number
            print(f"  created {number}: {inc['short_description']}")
        print(f"  -> try: python snow_main.py --incident {trigger_number}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
