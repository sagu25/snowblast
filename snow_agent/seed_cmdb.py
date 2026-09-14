"""Creates a realistic CMDB (configuration items + relationships) in your
ServiceNow instance, so the UI's CI Relationships tab has real, meaningful
data to render instead of leftover placeholder records.

This is the BlastRadius_Synthetic_CMDB_Data dataset: 15 configuration
items across a handful of ServiceNow CI classes, and 22 relationships
between them -- an Expense Management app depending on SSO, SAP Backend,
and Corporate Email; a Core Network Switch Fabric running several backend
databases; a CRM/reporting/sales cluster; and so on.

Usage:
    python -m snow_agent.seed_cmdb
    python -m snow_agent.seed_cmdb --dry-run

Needs the same SERVICENOW_* environment variables as snow_main.py.

Each CI is created directly in its own class table (cmdb_ci_appl,
cmdb_ci_db_instance, cmdb_ci_server) so it shows up with the right class
in ServiceNow's own CMDB Workspace map -- not as a generic "cmdb_ci"
record, which is what produces the "unnamed" nodes the CI Relationships
tab shows when the underlying data itself is generic/placeholder.
Relationships are created in cmdb_rel_ci with the correct cmdb_rel_type
looked up by name; "Depends on::Used by" and "Runs on::Runs" are both
standard relationship types already present on a stock instance.

The synthetic "CI-001" style IDs below are only used to wire up
relationships within this script -- real records get real ServiceNow
sys_ids on creation, and relationships are created against those, not the
synthetic IDs.
"""

from __future__ import annotations

import argparse
import sys

from snow_agent.client import NoCredentialsConfigured, ServiceNowClient, ServiceNowError

CIS = [
    {"id": "CI-001", "name": "Expense Management System", "class": "cmdb_ci_appl", "aliases": "expense app, EMS, expense"},
    {"id": "CI-002", "name": "SAP Backend", "class": "cmdb_ci_db_instance", "aliases": "SAP, ERP backend, SAP database"},
    {"id": "CI-003", "name": "HR Portal", "class": "cmdb_ci_appl", "aliases": "HR portal, employee self-service, ESS"},
    {"id": "CI-004", "name": "Payroll System", "class": "cmdb_ci_appl", "aliases": "payroll, salary system, pay system"},
    {"id": "CI-005", "name": "Single Sign-On (SSO)", "class": "cmdb_ci_appl", "aliases": "SSO, login service, identity provider, IdP"},
    {"id": "CI-006", "name": "Core Network Switch Fabric", "class": "cmdb_ci_server", "aliases": "network, switch fabric, core network"},
    {"id": "CI-007", "name": "Primary SQL Cluster", "class": "cmdb_ci_db_instance", "aliases": "SQL cluster, primary database, DB"},
    {"id": "CI-008", "name": "Procurement Portal", "class": "cmdb_ci_appl", "aliases": "procurement app, purchasing portal, P2P"},
    {"id": "CI-009", "name": "CRM Platform", "class": "cmdb_ci_appl", "aliases": "CRM, customer relationship management, sales platform"},
    {"id": "CI-010", "name": "Corporate Email Service", "class": "cmdb_ci_appl", "aliases": "email, messaging service, Outlook backend"},
    {"id": "CI-011", "name": "Vendor Payment Gateway", "class": "cmdb_ci_appl", "aliases": "payment gateway, vendor payments, AP gateway"},
    {"id": "CI-012", "name": "Benefits Enrollment System", "class": "cmdb_ci_appl", "aliases": "benefits system, enrollment portal, open enrollment"},
    {"id": "CI-013", "name": "Reporting Data Warehouse", "class": "cmdb_ci_db_instance", "aliases": "data warehouse, DW, reporting DB, analytics DB"},
    {"id": "CI-014", "name": "Sales Quoting Tool", "class": "cmdb_ci_appl", "aliases": "quoting tool, quote generator, sales quotes"},
    {"id": "CI-015", "name": "Contract Management System", "class": "cmdb_ci_appl", "aliases": "contract management, CLM, legal contracts system"},
]

# (parent synthetic id, child synthetic id, relationship type name)
RELATIONSHIPS = [
    ("CI-002", "CI-001", "Depends on::Used by"),
    ("CI-002", "CI-004", "Depends on::Used by"),
    ("CI-005", "CI-001", "Used by::Depends on"),
    ("CI-005", "CI-003", "Used by::Depends on"),
    ("CI-005", "CI-008", "Used by::Depends on"),
    ("CI-005", "CI-009", "Used by::Depends on"),
    ("CI-005", "CI-012", "Used by::Depends on"),
    ("CI-005", "CI-014", "Used by::Depends on"),
    ("CI-005", "CI-015", "Used by::Depends on"),
    ("CI-006", "CI-002", "Runs on::Runs"),
    ("CI-006", "CI-007", "Runs on::Runs"),
    ("CI-006", "CI-010", "Runs on::Runs"),
    ("CI-007", "CI-003", "Depends on::Used by"),
    ("CI-007", "CI-012", "Depends on::Used by"),
    ("CI-007", "CI-013", "Depends on::Used by"),
    ("CI-013", "CI-009", "Depends on::Used by"),
    ("CI-013", "CI-014", "Depends on::Used by"),
    ("CI-009", "CI-014", "Depends on::Used by"),
    ("CI-008", "CI-011", "Depends on::Used by"),
    ("CI-002", "CI-011", "Depends on::Used by"),
    ("CI-010", "CI-003", "Depends on::Used by"),
    ("CI-010", "CI-001", "Depends on::Used by"),
]


def _dv(value) -> str:
    if isinstance(value, dict):
        return value.get("value") or value.get("display_value") or ""
    return value or ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print what would be created, don't call ServiceNow")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"Would create {len(CIS)} configuration item(s):")
        for ci in CIS:
            print(f"  - {ci['name']} ({ci['class']})")
        print(f"\nWould create {len(RELATIONSHIPS)} relationship(s):")
        for parent, child, rel_type in RELATIONSHIPS:
            print(f"  - {parent} -> {child}  ({rel_type})")
        print("\n(dry run -- nothing created)")
        return 0

    try:
        client = ServiceNowClient()
    except NoCredentialsConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"Creating {len(CIS)} configuration items...\n")
    sys_ids: dict[str, str] = {}
    for ci in CIS:
        fields = {"name": ci["name"], "u_aliases": ci["aliases"]}
        try:
            record = client.create_ci(ci["class"], fields)
        except ServiceNowError as exc:
            print(f"  warning: create failed for {ci['name']} ({exc}); retrying without u_aliases")
            record = client.create_ci(ci["class"], {"name": ci["name"]})
        sys_id = _dv(record.get("sys_id"))
        sys_ids[ci["id"]] = sys_id
        print(f"  created {ci['name']} ({ci['class']}) -> {sys_id}")

    print(f"\nCreating {len(RELATIONSHIPS)} relationships...\n")
    rel_type_cache: dict[str, str] = {}
    created = 0
    for parent, child, rel_type in RELATIONSHIPS:
        if rel_type not in rel_type_cache:
            type_sys_id = client.get_rel_type_sys_id(rel_type)
            if type_sys_id is None:
                print(f"  warning: relationship type '{rel_type}' not found in cmdb_rel_type on this instance -- skipping all uses of it")
            rel_type_cache[rel_type] = type_sys_id or ""

        type_sys_id = rel_type_cache[rel_type]
        if not type_sys_id or parent not in sys_ids or child not in sys_ids:
            continue
        client.create_ci_relationship(sys_ids[parent], sys_ids[child], type_sys_id)
        created += 1

    print(f"  created {created}/{len(RELATIONSHIPS)} relationship(s)")
    print(f"\n-> point an incident's Configuration Item at '{CIS[0]['name']}' (or any of the above) and open the CI Relationships tab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
