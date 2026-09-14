"""Diagnostic: dumps exactly what ServiceNow's Table API returns for one
CI and its cmdb_rel_ci relationships -- no simplification, no _ref()
extraction, just the raw JSON. Use this when the CI Relationships tab
shows something that doesn't match what you see in ServiceNow's own CMDB
Workspace map, to see whether the two are actually looking at the same
underlying rows.

Usage:
    python -m snow_agent.debug_ci <ci_sys_id_or_name>

Needs the same SERVICENOW_* environment variables as snow_main.py.
"""

from __future__ import annotations

import json
import sys

from snow_agent.client import NoCredentialsConfigured, ServiceNowClient, ServiceNowError


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: python -m snow_agent.debug_ci <ci_sys_id_or_name>", file=sys.stderr)
        return 2

    identifier = argv[0]

    try:
        client = ServiceNowClient()
    except NoCredentialsConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        ci = client.get_ci(identifier)
    except ServiceNowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if ci is None:
        print(f"No cmdb_ci record found matching '{identifier}'")
        return 1

    print("=" * 72)
    print("CI RECORD (cmdb_ci)")
    print("=" * 72)
    print(json.dumps(ci, indent=2))

    sys_id = ci.get("sys_id")
    sys_id = sys_id.get("value") if isinstance(sys_id, dict) else sys_id

    try:
        rels = client.get_ci_relationships(sys_id)
    except ServiceNowError as exc:
        print(f"error fetching relationships: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 72)
    print(f"RAW cmdb_rel_ci ROWS WHERE parent={sys_id} OR child={sys_id}  ({len(rels)} found)")
    print("=" * 72)
    print(json.dumps(rels, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
