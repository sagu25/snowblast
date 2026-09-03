# Blast Radius Agent (ServiceNow)

Correlates a triggering ServiceNow incident against other ServiceNow data
to answer "is this isolated, or part of something wider?" — **no CMDB
required.** Instead of walking a maintained dependency graph, it searches
and scores other incidents by symptom, timing, location, and assignment
group, live, every time it runs.

Modeled on a reference prototype (a scripted UX simulator with no real
backend) but built as an actual working agent: real ServiceNow Table API
calls, a deterministic and auditable correlation engine, and Claude
layered on top only for narration and chat — never for the clustering
math itself.

This is presently a custom-built agent. It's expected to eventually be
replaced by a native agent on the Blueverse LTM platform — the UI and the
report's JSON shape are deliberately kept separate from this backend so
that swap only means pointing the UI at a different data source, not
rebuilding it.

## UI

`snow_agent/ui-mockup.html` — open it directly in a browser, no server
needed. It's populated with the exact numbers the real correlation engine
produces (the storm/isolated/false-positive scenarios in `correlate.py`'s
own validation run), shaped identically to `report.py`'s `to_json()`
output — so pointing it at a live backend later (this one, or the
Blueverse LTM-native agent it's slated to be replaced by) means swapping
the mock `SCENARIOS` object for a `fetch()`, not rebuilding the UI. Three
scenarios (storm cluster, isolated incident, false-positive cluster), the
Direct/Likely/Possible radial view, the 8-step timeline, an agent
narrative log, analyst decision buttons (Accept/Deeper analysis/Reject),
and an "Ask Blast Radius" chat.

## Setup

```
pip install -r requirements.txt
```

Set as environment variables (never hardcode credentials):

```
# PowerShell
$env:SERVICENOW_INSTANCE_URL = "https://devXXXXXX.service-now.com"
$env:SERVICENOW_USERNAME = "..."
$env:SERVICENOW_PASSWORD = "..."
```

Basic Auth against a Personal Developer Instance — the simplest thing
that works for a PDI. For the optional narration/chat features, also set
one of `ANTHROPIC_API_KEY` or `ANTHROPIC_FOUNDRY_API_KEY` +
`ANTHROPIC_FOUNDRY_RESOURCE` (Microsoft Foundry / Azure, for environments
where the first-party Anthropic API is blocked — see
`snow_agent/llm_client.py`, which auto-detects which to use).

## Seed some demo data

Fresh ServiceNow instance, nothing to correlate against yet? Create five
realistic incident clusters (a real storm cluster, an isolated ticket, a
false-positive cluster that should get fully excluded, a second real
cluster, and a mixed real+false cluster):

```
python -m snow_agent.seed_incidents --dry-run   # preview, creates nothing
python -m snow_agent.seed_incidents             # actually creates them
```

It prints each created incident's number and the exact `snow_main.py`
command to run against it. `location`/`assignment_group` default to
generic values in `seed_incidents.py` (`LOCATIONS`/`GROUPS` constants) —
if your instance doesn't have a matching location or group record, that
one field is dropped and the incident is still created (correlation just
leans more on category/timing/keywords for it). Edit those constants to
match what's actually in your instance for the full effect.

## Run it

```
python snow_main.py --incident INC0010023
python snow_main.py --incident INC0010023 --json
python snow_main.py --incident INC0010023 --hours 12
python snow_main.py --incident INC0010023 --narrate     # needs an LLM credential
python snow_main.py --incident INC0010023 --chat        # needs an LLM credential
python snow_main.py --incident INC0010023 --post-note   # writes back, asks to confirm first
```

## How it works

Mirrors the reference prototype's 8-step method, but for real:

1. **Trigger** — fetch the named incident from ServiceNow.
2. **Extract signals** — its location, assignment group, category, symptom
   keywords, and open time.
3. **Search** — pull other incidents opened within a time window (default
   ±6h, `--hours` to change) of the trigger.
4. **Form direct cluster** — score every candidate on 5 weighted signals
   (assignment group, location, category, time proximity, keyword overlap)
   and keep everything above threshold. See `correlate.py` for the exact
   weights — they're plain constants, not a black box.
5. **Expand likely impact** — pull `cmdb_ci`/`business_service` off the
   matched incidents, if populated. If not populated, the report says so
   explicitly rather than guessing.
6. **Expand possible impact** — locations, urgency, and who's affected,
   rolled up across the whole cluster.
7. **Challenge false positives** — re-examine each direct match's own
   `close_notes`/`work_notes` for contradicting language ("unrelated",
   "duplicate", "planned", etc.) and exclude it if found, lowering
   confidence accordingly.
8. **Prepare analyst decision** — package everything into a report. The
   agent never closes, re-prioritizes, or declares a major incident on its
   own; `--post-note` requires an explicit `y` confirmation before writing
   anything back.

## What's not built yet

- Only the `incident` table is correlated against. Problem records and
  change records (both called out in the reference prototype) aren't
  queried — `ServiceNowClient` would need `search_problems`/
  `search_changes` methods, and `correlate.py` would need to weigh that
  evidence in.
- No OAuth — Basic Auth only, which is fine for a PDI but likely not for
  a production ServiceNow instance.
- The chat (`--chat`) answers questions about the already-computed
  assessment; it doesn't re-query ServiceNow mid-conversation.
- The UI (`ui-mockup.html`) and this Python backend aren't wired together
  yet — same JSON shape, but the UI still reads a mock object rather than
  calling a live endpoint. A thin API layer (Flask/FastAPI wrapping
  `snow_agent`) would close that gap.

## Files

```
snow_main.py          entry point
requirements.txt
snow_agent/
  client.py         ServiceNow Table API wrapper (GET/POST/PATCH, Basic Auth)
  models.py          Incident / MatchedIncident / BlastRadiusAssessment
  correlate.py         the deterministic 8-step correlation engine
  report.py             text / JSON / work-note rendering
  narrate.py              Claude narration + grounded chat
  llm_client.py             Anthropic vs. Azure Foundry, auto-picked
  cli.py                      argument parsing
  seed_incidents.py             creates demo incident clusters for a fresh instance
  ui-mockup.html                  the console UI, see "UI" above
```
