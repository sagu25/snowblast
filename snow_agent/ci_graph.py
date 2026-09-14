"""Builds a CI relationship graph from ServiceNow's `cmdb_ci` /
`cmdb_rel_ci` tables -- the same data ServiceNow's own CI relationship
map (Dependency Views) is drawn from.

Deliberately one hop deep from the triggering incident's configuration
item: every CI directly related to it (parent or child), plus the
relationship type on each edge. No layout math happens here -- that's
the frontend's job; this module only returns nodes and edges.
"""

from __future__ import annotations

from snow_agent.client import ServiceNowClient


def _dv(value) -> str:
    if isinstance(value, dict):
        return value.get("display_value") or value.get("value") or ""
    return value or ""


def _ref(value) -> tuple[str, str]:
    """A reference field returned with sysparm_display_value=all -- pull
    out (sys_id, display name)."""
    if isinstance(value, dict):
        return value.get("value") or "", value.get("display_value") or ""
    return "", ""


def build_ci_graph(client: ServiceNowClient, ci_identifier: str) -> dict | None:
    ci = client.get_ci(ci_identifier)
    if ci is None:
        return None

    root_id = _dv(ci.get("sys_id"))
    root_label = _dv(ci.get("name")) or ci_identifier
    root_class = _dv(ci.get("sys_class_name")) or "cmdb_ci"
    root_status = _dv(ci.get("operational_status"))

    nodes: dict[str, dict] = {
        root_id: {
            "id": root_id,
            "label": root_label,
            "type": root_class,
            "status": root_status,
            "root": True,
        }
    }
    edges: list[dict] = []

    for rel in client.get_ci_relationships(root_id):
        p_id, p_label = _ref(rel.get("parent"))
        c_id, c_label = _ref(rel.get("child"))
        rel_type = _dv(rel.get("type"))

        if p_id and p_id not in nodes:
            nodes[p_id] = {"id": p_id, "label": p_label or p_id, "type": "cmdb_ci", "root": False}
        if c_id and c_id not in nodes:
            nodes[c_id] = {"id": c_id, "label": c_label or c_id, "type": "cmdb_ci", "root": False}
        if p_id and c_id:
            edges.append({"source": p_id, "target": c_id, "label": rel_type or "related to"})

    return {
        "root": root_id,
        "root_label": root_label,
        "nodes": list(nodes.values()),
        "edges": edges,
    }
