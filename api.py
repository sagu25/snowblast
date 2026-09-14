"""Thin HTTP layer over snow_agent, for the React UI in web/.

Every endpoint just calls the same functions snow_main.py's CLI calls --
there is no logic here beyond request/response plumbing. Credential
errors (ServiceNow or the LLM) are caught and returned as clean JSON with
a 503, the same "not configured yet" story as the CLI, not a stack trace.

Run with: python api.py
The React dev server (web/) proxies /api/* here -- see web/vite.config.js.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from flask import Flask, jsonify, request

from snow_agent.client import NoCredentialsConfigured, ServiceNowClient, ServiceNowError
from snow_agent.correlate import assess
from snow_agent.llm_client import NoCredentialsConfigured as NoLLMCredentials
from snow_agent.models import Incident
from snow_agent.report import to_json as assessment_to_json, to_work_note

app = Flask(__name__)

# In-memory only -- holds the last assessment per incident number so
# /narrate, /chat, /post-note don't have to re-run correlation. Fine for a
# single-user dev tool; would need a real store for anything else.
_CACHE: dict[str, object] = {}


def _load_assessment(number: str, hours: float):
    client = ServiceNowClient()
    trigger_record = client.get_incident(number)
    if trigger_record is None:
        return None, None
    trigger = Incident.from_record(trigger_record)

    opened = (
        datetime.strptime(trigger.opened_at, "%Y-%m-%d %H:%M:%S")
        if trigger.opened_at
        else datetime.utcnow()
    )
    window = timedelta(hours=hours)
    candidate_records = client.search_incidents(
        exclude_sys_id=trigger.sys_id,
        opened_after=(opened - window).strftime("%Y-%m-%d %H:%M:%S"),
        opened_before=(opened + window).strftime("%Y-%m-%d %H:%M:%S"),
    )
    candidates = [Incident.from_record(r) for r in candidate_records]
    assessment = assess(trigger, candidates)
    return client, assessment


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/incident/<number>")
def get_assessment(number: str):
    hours = float(request.args.get("hours", 6))
    try:
        client, assessment = _load_assessment(number, hours)
    except NoCredentialsConfigured as exc:
        return jsonify({"error": "servicenow_not_configured", "message": str(exc)}), 503
    except ServiceNowError as exc:
        return jsonify({"error": "servicenow_error", "message": str(exc)}), 502

    if assessment is None:
        return jsonify({"error": "not_found", "message": f"no incident found matching '{number}'"}), 404

    _CACHE[number] = assessment
    return assessment_to_json(assessment), 200, {"Content-Type": "application/json"}


@app.post("/api/incident/<number>/narrate")
def narrate_assessment(number: str):
    assessment = _CACHE.get(number)
    if assessment is None:
        return jsonify({"error": "not_found", "message": "call GET /api/incident/<number> first"}), 404
    try:
        from snow_agent.narrate import narrate

        text = narrate(assessment)
    except NoLLMCredentials as exc:
        return jsonify({"error": "llm_not_configured", "message": str(exc)}), 503
    return jsonify({"narrative": text})


@app.post("/api/incident/<number>/chat")
def chat_assessment(number: str):
    assessment = _CACHE.get(number)
    if assessment is None:
        return jsonify({"error": "not_found", "message": "call GET /api/incident/<number> first"}), 404
    question = (request.get_json(silent=True) or {}).get("question", "")
    if not question.strip():
        return jsonify({"error": "bad_request", "message": "missing 'question'"}), 400
    try:
        from snow_agent.narrate import ask

        answer = ask(assessment, question)
    except NoLLMCredentials as exc:
        return jsonify({"error": "llm_not_configured", "message": str(exc)}), 503
    return jsonify({"answer": answer})


@app.get("/api/incident/<number>/ci-graph")
def ci_graph(number: str):
    assessment = _CACHE.get(number)
    if assessment is None:
        return jsonify({"error": "not_found", "message": "call GET /api/incident/<number> first"}), 404

    ci_name = assessment.trigger.cmdb_ci or assessment.trigger.business_service
    if not ci_name:
        return jsonify({
            "error": "no_ci",
            "message": "the triggering incident has no configuration item (cmdb_ci) set, so there is no CI relationship map to draw",
        }), 404

    try:
        from snow_agent.ci_graph import build_ci_graph

        client = ServiceNowClient()
        graph = build_ci_graph(client, ci_name)
    except NoCredentialsConfigured as exc:
        return jsonify({"error": "servicenow_not_configured", "message": str(exc)}), 503
    except ServiceNowError as exc:
        return jsonify({"error": "servicenow_error", "message": str(exc)}), 502

    if graph is None:
        return jsonify({"error": "not_found", "message": f"CI '{ci_name}' not found in cmdb_ci"}), 404

    return jsonify(graph)


def _dv(value):
    if isinstance(value, dict):
        return value.get("display_value") or value.get("value") or ""
    return value or ""


@app.get("/api/ci")
def list_cis():
    """Full (optionally filtered) pick-list of configuration items from
    cmdb_ci -- lets the UI offer every CI in the CMDB, not just whatever a
    single incident's cmdb_ci field happens to reference (which may be
    blank, free text, or stale, as incidents commonly are)."""
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 100))
    try:
        client = ServiceNowClient()
        records = client.list_cis(query=q or None, limit=limit)
    except NoCredentialsConfigured as exc:
        return jsonify({"error": "servicenow_not_configured", "message": str(exc)}), 503
    except ServiceNowError as exc:
        return jsonify({"error": "servicenow_error", "message": str(exc)}), 502

    items = [
        {
            "id": _dv(r.get("sys_id")),
            "label": _dv(r.get("name")) or _dv(r.get("sys_id")),
            "type": _dv(r.get("sys_class_name")),
        }
        for r in records
    ]
    return jsonify({"items": items})


@app.get("/api/ci/<ci_id>/graph")
def ci_graph_by_id(ci_id: str):
    """Same shape as /api/incident/<number>/ci-graph, but rooted at any CI
    sys_id/name directly -- lets the UI let the user pick a related CI from
    the list and drill into *its* relationships, not just the one attached
    to the triggering incident."""
    try:
        from snow_agent.ci_graph import build_ci_graph

        client = ServiceNowClient()
        graph = build_ci_graph(client, ci_id)
    except NoCredentialsConfigured as exc:
        return jsonify({"error": "servicenow_not_configured", "message": str(exc)}), 503
    except ServiceNowError as exc:
        return jsonify({"error": "servicenow_error", "message": str(exc)}), 502

    if graph is None:
        return jsonify({"error": "not_found", "message": f"CI '{ci_id}' not found in cmdb_ci"}), 404

    return jsonify(graph)


@app.post("/api/incident/<number>/post-note")
def post_note(number: str):
    assessment = _CACHE.get(number)
    if assessment is None:
        return jsonify({"error": "not_found", "message": "call GET /api/incident/<number> first"}), 404
    body = request.get_json(silent=True) or {}
    if not body.get("confirm"):
        return jsonify({"error": "confirmation_required", "message": "pass {\"confirm\": true} to actually write to ServiceNow"}), 400
    try:
        client = ServiceNowClient()
        client.post_work_note(assessment.trigger.sys_id, to_work_note(assessment))
    except NoCredentialsConfigured as exc:
        return jsonify({"error": "servicenow_not_configured", "message": str(exc)}), 503
    except ServiceNowError as exc:
        return jsonify({"error": "servicenow_error", "message": str(exc)}), 502
    return jsonify({"posted": True, "incident": number})


if __name__ == "__main__":
    app.run(port=5057, debug=True)
