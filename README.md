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

## 1. Setup

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

Until these are set, every entry point below (CLI, API, UI) fails with a
clean, explicit error naming exactly which variable is missing — never a
stack trace, and never silently.

## 2. Seed some demo data

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

**How ticket creation actually works**, for the same reason section "How
it works" below spells out correlation instead of just saying "it
correlates":

1. Each scenario in `seed_incidents.py`'s `SCENARIOS` list is a plain
   Python dict per incident — `short_description`, `description`,
   `location`, `assignment_group`, `category`, `priority`,
   `minutes_ago` (converted to a real `opened_at` timestamp relative to
   *when you run the script*, not hardcoded dates — so seeded incidents
   always land inside the default 6-hour correlation window no matter
   when you seed them).
2. `build_fields()` turns that into the field dict the Table API expects.
3. `ServiceNowClient.create_incident()` — new, added specifically for
   this script — is a plain `POST /api/now/table/incident` (see
   `client.py`'s `_post`). It's a separate write path from
   `post_work_note()`, which is the *only* write the agent's own
   assess/report flow ever makes; `create_incident` is never called
   during normal correlation, only by this seed script.
4. `location`/`assignment_group` are ServiceNow *reference* fields — the
   write only succeeds if a record with that exact display value already
   exists in your instance. `create_with_fallback()` tries the full write
   first; if ServiceNow rejects it, it retries the same incident without
   those two fields rather than aborting the whole run, so seeding still
   completes even on a completely stock instance. You lose some
   correlation signal on that record (only category/timing/keywords are
   left to match on), which is exactly the tradeoff the fallback message
   prints out loud when it happens.
5. Nothing here declares which incidents are "related" — that would
   defeat the point. The clusters only exist because their fields happen
   to overlap; `correlate.py` has to (re)discover that from scratch when
   you actually run `snow_main.py` against one, same as it would against
   real, un-seeded ServiceNow data.

## 3. Run it — CLI

```
python snow_main.py --incident INC0010023
python snow_main.py --incident INC0010023 --json
python snow_main.py --incident INC0010023 --hours 12
python snow_main.py --incident INC0010023 --narrate     # needs an LLM credential
python snow_main.py --incident INC0010023 --chat        # needs an LLM credential
python snow_main.py --incident INC0010023 --post-note   # writes back, asks to confirm first
```

## 4. Run it — the real UI (`web/`)

A full React app wired to the live backend via a small API server — not
the static mockup in section 5.

```
# Terminal 1 — the API
python api.py                    # http://localhost:5057

# Terminal 2 — the UI
cd web
npm install
npm run dev                      # prints the URL, usually http://localhost:5173
```

Open the printed URL, type a ServiceNow incident number in the top bar
(one that `seed_incidents.py` printed, or any real one), and click
**Analyze**. Without ServiceNow credentials set yet, you'll see a clean
"ServiceNow not configured" card instead of a crash — exactly like the
CLI's error, just rendered. Once section 1's env vars are set, the same
running servers start returning real data with no code changes.

What it does: the top-bar incident lookup runs a live `GET
/api/incident/<number>`; the center panel renders the actual
Direct/Likely/Possible radial view from that response; the right panel is
the full assessment breakdown, with a **Narrate** button that calls
Claude (needs an LLM credential — shows a clear inline error otherwise,
doesn't crash); the bottom bar has real analyst actions — **Accept** asks
you to confirm, then actually posts a work note to ServiceNow; **Deeper
analysis** re-runs the search with a doubled time window; **Reject**
discards client-side, no write. The floating chat calls the same grounded
`ask()` the CLI's `--chat` uses.

`api.py` is a thin Flask layer — every endpoint just calls the same
`snow_agent` functions `snow_main.py` does; there's no logic in it beyond
request/response plumbing and turning credential errors into clean JSON
(503) instead of a stack trace.

## 5. Static UI mockup (no backend, no setup)

`snow_agent/ui-mockup.html` — open it directly in a browser, no server
needed, no credentials needed. It's populated with the exact numbers the
real correlation engine produces (the storm/isolated/false-positive
scenarios in `correlate.py`'s own validation run), shaped identically to
`report.py`'s `to_json()` output. Useful for a quick look or a
presentation without spinning up the full stack; section 4's `web/` is
the one wired to live data.

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
   own; `--post-note` / the UI's Accept button both require an explicit
   confirmation before writing anything back.

## Troubleshooting

- **`error: set SERVICENOW_INSTANCE_URL, ...`** — see section 1; none of
  the three ServiceNow env vars are optional.
- **Web UI shows "ServiceNow not configured yet"** — same cause as above,
  just surfaced in the UI instead of a terminal. Set the env vars where
  `python api.py` runs, then restart it (env vars are only read at
  startup).
- **`--narrate`/`--chat`/the Narrate button/the chat panel show a
  credential error** — the LLM credential (`ANTHROPIC_API_KEY` or the
  `ANTHROPIC_FOUNDRY_*` pair) isn't set. Everything else works without it.
- **Seeded incidents don't form the expected cluster** — `location`/
  `assignment_group` in `seed_incidents.py` may not match real records in
  your instance, so that field got silently dropped on creation (see
  section 2). Edit `LOCATIONS`/`GROUPS` to match your instance, or widen
  `--hours` if timing is the only signal left to match on.
- **`npm`/`node` not recognized** — install Node.js from nodejs.org
  (bundles npm), then reopen your terminal. Built and tested on Node 22.
- **Vite dev server picks a different port than 5173** — it prints
  whichever port it actually bound to (something else may already be
  using 5173); use the printed URL, not an assumed one.

## What's not built yet

- Only the `incident` table is correlated against. Problem records and
  change records (both called out in the reference prototype) aren't
  queried — `ServiceNowClient` would need `search_problems`/
  `search_changes` methods, and `correlate.py` would need to weigh that
  evidence in.
- No OAuth — Basic Auth only, which is fine for a PDI but likely not for
  a production ServiceNow instance.
- The chat (`--chat` / the web UI's chat) answers questions about the
  already-computed assessment; it doesn't re-query ServiceNow
  mid-conversation.
- `api.py` runs Flask's development server (`app.run(debug=True)`) —
  fine for local use, not meant to be exposed as-is.
- `api.py` caches the last assessment per incident number in memory —
  fine for one person testing locally, not for concurrent/multi-user use.

## Files

```
snow_main.py          CLI entry point
api.py                  Flask API for the React UI (thin wrapper, no logic)
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
  ui-mockup.html                  static UI mockup (no backend), see section 5
web/                    the real React app, wired to api.py (section 4)
  vite.config.js          dev-server proxy to api.py
  src/
    App.jsx                 top-level state: lookup, assessment, theme, chat
    api.js                    fetch wrapper, typed ApiError on non-2xx
    components/
      TopBar.jsx                incident-number lookup, hours window, theme
      LeftPane.jsx                trigger incident card, evidence sources
      RadialView.jsx                the live Direct/Likely/Possible SVG view
      AssessmentPanel.jsx            confidence, matches, narrate button
      BottomBar.jsx                    step timeline, log, analyst actions
      ChatPanel.jsx                      Ask Blast Radius, grounded chat
```
