"""ServiceNow Table API client.

Credentials are read only from the environment, never hardcoded:
  - SERVICENOW_INSTANCE_URL   e.g. https://dev123456.service-now.com
  - SERVICENOW_USERNAME
  - SERVICENOW_PASSWORD

Basic Auth against a Personal Developer Instance is the default -- the
simplest thing that works for a PDI. If you later need OAuth, swap the
`_auth()`/`_headers()` methods; nothing above this layer (correlate.py,
report.py) knows or cares how requests are authenticated.
"""

from __future__ import annotations

import os

import requests

DEFAULT_FIELDS = [
    "sys_id",
    "number",
    "short_description",
    "description",
    "opened_at",
    "location",
    "assignment_group",
    "category",
    "state",
    "priority",
    "cmdb_ci",
    "business_service",
    "work_notes",
    "close_notes",
]

CI_FIELDS = ["sys_id", "name", "sys_class_name", "operational_status"]

CI_REL_FIELDS = ["sys_id", "type", "parent", "child"]


class NoCredentialsConfigured(RuntimeError):
    pass


class ServiceNowError(RuntimeError):
    pass


class ServiceNowClient:
    def __init__(
        self,
        instance_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 15.0,
    ):
        self.instance_url = (instance_url or os.environ.get("SERVICENOW_INSTANCE_URL") or "").rstrip("/")
        self.username = username or os.environ.get("SERVICENOW_USERNAME")
        self.password = password or os.environ.get("SERVICENOW_PASSWORD")
        self.timeout = timeout

        if not self.instance_url or not self.username or not self.password:
            raise NoCredentialsConfigured(
                "set SERVICENOW_INSTANCE_URL, SERVICENOW_USERNAME, and "
                "SERVICENOW_PASSWORD as environment variables"
            )

    def _get(self, table: str, params: dict) -> list[dict]:
        url = f"{self.instance_url}/api/now/table/{table}"
        params = {"sysparm_display_value": "all", **params}
        resp = requests.get(
            url,
            params=params,
            auth=(self.username, self.password),
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise ServiceNowError("authentication rejected -- check SERVICENOW_USERNAME/SERVICENOW_PASSWORD")
        if not resp.ok:
            raise ServiceNowError(f"GET {table} failed: {resp.status_code} {resp.text[:300]}")
        return resp.json().get("result", [])

    def _patch(self, table: str, sys_id: str, body: dict) -> dict:
        url = f"{self.instance_url}/api/now/table/{table}/{sys_id}"
        resp = requests.patch(
            url,
            json=body,
            auth=(self.username, self.password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise ServiceNowError("authentication rejected -- check SERVICENOW_USERNAME/SERVICENOW_PASSWORD")
        if not resp.ok:
            raise ServiceNowError(f"PATCH {table}/{sys_id} failed: {resp.status_code} {resp.text[:300]}")
        return resp.json().get("result", {})

    def get_incident(self, number_or_sys_id: str) -> dict | None:
        """Look up one incident by number (INC0010023) or sys_id."""
        query = f"number={number_or_sys_id}^ORsys_id={number_or_sys_id}"
        records = self._get(
            "incident",
            {"sysparm_query": query, "sysparm_fields": ",".join(DEFAULT_FIELDS), "sysparm_limit": 1},
        )
        return records[0] if records else None

    def search_incidents(
        self,
        exclude_sys_id: str,
        opened_after: str | None = None,
        opened_before: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Candidate incidents to correlate against -- a time-windowed
        search, not filtered by symptom yet (that scoring happens in
        correlate.py, in code we can audit, not in a query string)."""
        clauses = [f"sys_id!={exclude_sys_id}"]
        if opened_after:
            clauses.append(f"opened_at>={opened_after}")
        if opened_before:
            clauses.append(f"opened_at<={opened_before}")
        query = "^".join(clauses) + "^ORDERBYDESCopened_at"
        return self._get(
            "incident",
            {"sysparm_query": query, "sysparm_fields": ",".join(DEFAULT_FIELDS), "sysparm_limit": limit},
        )

    def get_ci(self, sys_id_or_name: str) -> dict | None:
        """Look up one configuration item by sys_id or name, from the
        `cmdb_ci` table -- the same record ServiceNow's own CI relationship
        map is drawn from."""
        query = f"sys_id={sys_id_or_name}^ORname={sys_id_or_name}"
        records = self._get(
            "cmdb_ci",
            {"sysparm_query": query, "sysparm_fields": ",".join(CI_FIELDS), "sysparm_limit": 1},
        )
        return records[0] if records else None

    def list_cis(self, query: str | None = None, limit: int = 100) -> list[dict]:
        """Browse the `cmdb_ci` table directly, optionally filtered by a
        name substring. Exists so the UI can offer a full pick-list of
        configuration items instead of depending entirely on one incident's
        `cmdb_ci` reference, which may be blank, free text, or stale."""
        clauses = []
        if query:
            safe = query.replace("^", "").replace("=", "")
            clauses.append(f"nameLIKE{safe}")
        clauses.append("ORDERBYname")
        return self._get(
            "cmdb_ci",
            {"sysparm_query": "^".join(clauses), "sysparm_fields": ",".join(CI_FIELDS), "sysparm_limit": limit},
        )

    def get_ci_relationships(self, ci_sys_id: str, limit: int = 200) -> list[dict]:
        """Every relationship row (`cmdb_rel_ci`) where this CI is either
        the parent or the child -- the raw edges behind ServiceNow's CI
        relationship / dependency map."""
        query = f"parent={ci_sys_id}^ORchild={ci_sys_id}"
        return self._get(
            "cmdb_rel_ci",
            {"sysparm_query": query, "sysparm_fields": ",".join(CI_REL_FIELDS), "sysparm_limit": limit},
        )

    def post_work_note(self, sys_id: str, note: str) -> dict:
        """Append a work note. This is the only write path the agent's
        normal flow uses, and it's never called except when a human
        explicitly approves it (see snow_agent/cli.py --post-note)."""
        return self._patch("incident", sys_id, {"work_notes": note})

    def _post(self, table: str, body: dict) -> dict:
        url = f"{self.instance_url}/api/now/table/{table}"
        resp = requests.post(
            url,
            json=body,
            auth=(self.username, self.password),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise ServiceNowError("authentication rejected -- check SERVICENOW_USERNAME/SERVICENOW_PASSWORD")
        if not resp.ok:
            raise ServiceNowError(f"POST {table} failed: {resp.status_code} {resp.text[:300]}")
        return resp.json().get("result", {})

    def create_incident(self, fields: dict) -> dict:
        """Create an incident record. Not used by the agent's normal
        assess/report flow at all -- this exists solely for
        seed_incidents.py to populate demo data in a dev instance."""
        return self._post("incident", fields)
