from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta

from snow_agent.client import NoCredentialsConfigured, ServiceNowClient, ServiceNowError
from snow_agent.correlate import assess
from snow_agent.models import Incident
from snow_agent.report import to_json, to_text, to_work_note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="snow-blast-radius",
        description="ServiceNow-based blast radius agent -- correlates a trigger incident against ServiceNow data, no CMDB required.",
    )
    parser.add_argument("--incident", required=True, help="Incident number (e.g. INC0010023) or sys_id")
    parser.add_argument("--hours", type=float, default=6.0, help="Time window (hours, each direction) to search for related incidents (default: 6)")
    parser.add_argument("--json", action="store_true", help="emit the report as JSON")
    parser.add_argument("--narrate", action="store_true", help="add a Claude-generated plain-language summary (needs an LLM credential)")
    parser.add_argument("--chat", action="store_true", help="after the report, ask follow-up questions grounded in it (needs an LLM credential)")
    parser.add_argument("--post-note", action="store_true", help="write the assessment back to ServiceNow as a work note -- requires explicit human confirmation")
    args = parser.parse_args(argv)

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        client = ServiceNowClient()
    except NoCredentialsConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        trigger_record = client.get_incident(args.incident)
        if trigger_record is None:
            print(f"error: no incident found matching '{args.incident}'", file=sys.stderr)
            return 1
        trigger = Incident.from_record(trigger_record)

        opened = datetime.strptime(trigger.opened_at, "%Y-%m-%d %H:%M:%S") if trigger.opened_at else datetime.utcnow()
        window = timedelta(hours=args.hours)
        candidate_records = client.search_incidents(
            exclude_sys_id=trigger.sys_id,
            opened_after=(opened - window).strftime("%Y-%m-%d %H:%M:%S"),
            opened_before=(opened + window).strftime("%Y-%m-%d %H:%M:%S"),
        )
    except ServiceNowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    candidates = [Incident.from_record(r) for r in candidate_records]
    assessment = assess(trigger, candidates)

    print(to_json(assessment) if args.json else to_text(assessment))

    if args.narrate:
        from snow_agent.narrate import narrate

        print("\n[NARRATIVE]")
        print(narrate(assessment))

    if args.post_note:
        confirm = input(f"\nPost this assessment to {trigger.number} as a work note? [y/N] ")
        if confirm.strip().lower() == "y":
            client.post_work_note(trigger.sys_id, to_work_note(assessment))
            print(f"Posted to {trigger.number}.")
        else:
            print("Not posted.")

    if args.chat:
        from snow_agent.narrate import ask

        print("\n[ASK BLAST RADIUS] (blank line to exit)")
        while True:
            try:
                question = input("> ")
            except (EOFError, KeyboardInterrupt):
                break
            if not question.strip():
                break
            print(ask(assessment, question))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
