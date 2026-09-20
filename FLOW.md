# How To Run This, And How To Explain It

One document, two jobs: get the app running from a cold start, and give
you ready-to-use language for explaining it to anyone — a teammate, an
engineer, or leadership — without reading code at them.

---

## Part 1 — Run it, start to finish

### Prerequisites

- Python 3.10+, Node.js 18+ (built/tested on Node 22)
- A ServiceNow Personal Developer Instance (PDI) — URL + a user with
  `incident` table read/write access
- Optional, only needed for the Narrate/Chat buttons: an Azure OpenAI
  resource with a deployed chat model, plus its deployment name

Nothing below works with fake credentials — every entry point fails with
an explicit, named error ("set SERVICENOW_INSTANCE_URL...") instead of a
silent wrong answer, so you always know exactly what state you're in.

### Step 1 — Install

```powershell
cd snowblast
pip install -r requirements.txt
```

Installs `openai`, `requests`, `flask`. No Node dependency yet — that's
only needed if you run the web UI (Step 4).

### Step 2 — Set credentials (environment variables only, never hardcoded)

```powershell
$env:SERVICENOW_INSTANCE_URL = "https://devXXXXXX.service-now.com"
$env:SERVICENOW_USERNAME = "..."
$env:SERVICENOW_PASSWORD = "..."

# Optional -- only needed for Narrate / chat:
$env:AZURE_OPENAI_API_KEY = "..."
$env:AZURE_OPENAI_ENDPOINT = "https://your-resource.openai.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT = "..."     # the deployment name in Azure AI Foundry, not the model name
```

These only last for the current terminal session — set them again each
time you open a new one, or add them to your PowerShell profile.

### Step 3 — Put test data in ServiceNow

Skip this if you already have real incidents to point it at.

```powershell
python -m snow_agent.seed_incidents --dry-run   # preview, creates nothing
python -m snow_agent.seed_incidents             # actually creates them in ServiceNow
```

What you'll see: it prints something like

```
Created INC0010042  (storm cluster, 1 of 4)
Created INC0010043  (storm cluster, 2 of 4)
...
Try:  python snow_main.py --incident INC0010042
```

Five realistic clusters get created: a real "storm" cluster (several
incidents that should correlate), an isolated one-off, a false-positive
cluster (looks related but its own notes say it isn't — should get
excluded), a second real cluster, and a mixed cluster. Go check your
ServiceNow instance's incident list — they're really there.

### Step 4a — Run it from the terminal (CLI)

```powershell
python snow_main.py --incident INC0010042
python snow_main.py --incident INC0010042 --json
python snow_main.py --incident INC0010042 --hours 12
python snow_main.py --incident INC0010042 --narrate     # needs Azure OpenAI creds
python snow_main.py --incident INC0010042 --chat         # needs Azure OpenAI creds
python snow_main.py --incident INC0010042 --post-note    # writes back, asks y/N first
```

You'll see a plain-text report: the trigger incident, every correlated
match with its score and reason, likely/possible impact, and a final
confidence number.

### Step 4b — Run the real web UI

Two terminals, both stay open:

```powershell
# Terminal 1
python api.py
# -> Running on http://localhost:5057
```

```powershell
# Terminal 2
cd web
npm install      # first time only
npm run dev
# -> Local: http://localhost:5173/  (or another port if 5173 is busy)
```

Open the printed URL. Type an incident number from Step 3 into the top
bar, click **Analyze**. You'll see the radial Direct/Likely/Possible
view populate live, the right-hand panel with the full breakdown, and
(if Azure OpenAI is set) a working **Narrate** button and chat.

If you skip Step 2 entirely, the UI still runs — it just shows a clean
"ServiceNow not configured yet" card instead of crashing. That's
intentional: a missing credential is not a bug, it's an unfinished setup
step, and the app says so plainly.

### Step 5 — Static mockup, no setup at all

`snow_agent/ui-mockup.html` — just double-click it, opens in a browser,
no server, no credentials. It's not live, but it's shaped exactly like
the real report and useful for a 10-second look without booting anything.

---

## Part 2 — The architecture, in one picture

```
                         ServiceNow (your PDI)
                                 ▲
                    GET/POST (Table API, Basic Auth)
                                 │
                        ┌────────┴────────┐
                        │   snow_agent/    │
                        │                  │
                        │  client.py       │  ServiceNow HTTP calls (incident + cmdb_ci/cmdb_rel_ci)
                        │  models.py       │  raw JSON -> Incident objects
                        │  correlate.py    │  the 8-step scoring engine (deterministic)
                        │  report.py       │  Incident data -> JSON/text/work-note
                        │  narrate.py      │  optional: LLM narration + chat
                        │  llm_client.py   │  builds the Azure OpenAI client
                        │  ci_graph.py     │  builds a 1-hop CI relationship graph (nodes+edges)
                        └────────┬─────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                              │
           snow_main.py (CLI)              api.py (Flask)
           direct terminal entry           thin HTTP wrapper, no logic
                                                  │
                                            web/ (React)
                                            browser UI, fetch()
```

Two front doors, one engine. The CLI and the web UI both call the exact
same `correlate.py` / `report.py` functions — nothing is reimplemented
between them. If they ever disagree on a number, that's a bug.

There are two independent data views built on the same ServiceNow
instance, and it matters that you keep them mentally separate:

1. **Blast Radius correlation** (`correlate.py`) — works entirely off
   the `incident` table. Explicitly does **not** need a CMDB — that's
   the whole point of the design (see Part 5, "why not use the CMDB").
2. **CI Relationships** (`ci_graph.py`) — a separate tab in the UI that
   *does* read the CMDB (`cmdb_ci` / `cmdb_rel_ci`), to answer a
   different question: "what else is technically connected to this
   incident's configuration item?" This was added later, sits next to
   the correlation feature, and never feeds into its scoring — a CI
   graph edge never changes a confidence number.

### What happens on one lookup

| # | Step | Where | What it actually does |
|---|------|-------|------------------------|
| 1 | You provide an incident number | CLI flag / web top bar | e.g. `INC0010042` |
| 2 | Fetch the trigger | `client.get_incident()` | One GET to ServiceNow's Table API |
| 3 | Parse it | `models.Incident.from_record()` | Unwraps ServiceNow's reference-field wrappers into a plain object |
| 4 | Search candidates | `client.search_incidents()` | GET every other incident opened within ±6h (`--hours` to widen) of the trigger |
| 5 | Extract signals | `correlate.assess()` | Location, assignment group, category, keywords, open time — off the trigger |
| 6 | Score every candidate | `correlate._score()` | 5 weighted signals: assignment group (.25), location (.20), category (.15), time proximity (.15), keyword overlap (.25) |
| 7 | Form direct cluster | `correlate.assess()` | Anything scoring ≥ 0.5 |
| 8 | Challenge false positives | `correlate._challenge()` | Re-reads each match's own notes for contradicting language; excludes and lowers confidence if found |
| 9 | Expand likely/possible impact | `correlate.assess()` | Pulls affected systems, locations, urgency off whatever's left in the cluster |
| 10 | Package the report | `report.py` | `to_json()` / `to_text()` / `to_work_note()` |
| 11 | *(optional)* Narrate | `narrate.narrate()` | Sends the **finished assessment**, not raw ServiceNow data, to Azure OpenAI for a plain-language summary |
| 12 | *(optional)* Chat | `narrate.ask()` | Same idea — grounded Q&A over the assessment only |
| 13 | *(optional)* Post note | `client.post_work_note()` | Only fires on explicit confirmation. The only write in the normal flow. |

**The one fact to hold onto:** the LLM never computes a number. Steps
5–9 are plain arithmetic — you could hand-calculate any score yourself
from the constants at the top of `correlate.py`. The LLM only reads back
a result that already exists.

`seed_incidents.py` sits outside this flow entirely — a separate,
one-time utility that creates incidents via `client.create_incident()`,
a write path `assess()` never touches.

### What happens on the CI Relationships tab (separate feature)

This is a second, independent path through the same UI — it runs
alongside the Blast Radius flow above, not as part of it.

| # | Step | Where | What it actually does |
|---|------|-------|------------------------|
| 1 | User clicks the "CI Relationships" tab | `App.jsx` | Defaults to the trigger incident's own `cmdb_ci` field, if it has one |
| 2 | Look up the CI | `client.get_ci()` | GET against `cmdb_ci` by sys_id or name |
| 3 | Fetch relationships | `client.get_ci_relationships()` | GET `cmdb_rel_ci` rows where the CI is parent or child |
| 4 | Resolve real classes | `ci_graph._ref()` | Pulls each related record's actual class (`cmdb_ci_appl`, `cmdb_ci_db_instance`, ...) off the reference field's link URL — without this every node would show as a generic "cmdb_ci" |
| 5 | Build the graph | `ci_graph.build_ci_graph()` | Returns one hop of nodes + edges from the root CI — no multi-hop traversal, no layout math (that's the frontend's job) |
| 6 | Render | `CiGraphView.jsx` | Draws the graph |
| 7 | *(optional)* Browse any CI | `GET /api/ci` → `CiList.jsx` | Full searchable CMDB browser, for when the incident's own `cmdb_ci` field is blank, free text, or stale — a common real-world case this replaced a hard failure for |
| 8 | *(optional)* Re-root the graph | `GET /api/ci/<id>/graph` | Picking any CI from the browser re-draws the graph rooted there, decoupled from the original incident |

`seed_cmdb.py` is the CMDB equivalent of `seed_incidents.py` — a
one-time, idempotent utility (safe to re-run; it looks up CIs/relationships
by name first and reuses them) that creates 15 configuration items and 22
relationships across realistic ServiceNow CI classes, so this tab has
real data to show on a fresh instance. `debug_ci.py` is a pure diagnostic
(`python -m snow_agent.debug_ci <ci_sys_id_or_name>`) that dumps the raw
`cmdb_ci` / `cmdb_rel_ci` JSON for one CI, for when the graph doesn't
match what ServiceNow's own CMDB Workspace map shows. Neither script
touches the `incident` table or the correlation engine.

---

## Part 3 — How to explain it, by audience

### The 30-second version (anyone, hallway conversation)

> When a ServiceNow incident comes in, is it a one-off or the start of
> something bigger? Right now someone has to manually check. This agent
> checks automatically — it scores every other open incident against the
> new one on team, location, category, timing, and wording, flags what's
> actually related, and double-checks itself by reading each match's own
> notes for anything that says "actually unrelated." It never acts on its
> own — a human always approves before anything gets written back.

### The 3-minute version (a colleague, technical enough to want the "how")

> This solves one problem: when a ServiceNow incident comes in, is it
> isolated, or the first sign of something wider? Today that's a judgment
> call made by manually scanning other open tickets.
>
> Give it one incident number and it searches every other incident opened
> around the same time, and scores each one on five things: same team,
> same location, same category, how close in time, and how much the
> wording overlaps. Anything scoring high enough forms a cluster.
>
> Then it does something most correlation tools skip: it double-checks
> itself. For every match, it goes back and reads that ticket's own
> resolution notes for anything contradicting a shared cause — words like
> "unrelated" or "planned maintenance." If it finds that, it throws the
> match out and says so, instead of quietly overcounting.
>
> What comes back is a plain report: how many related incidents, which
> locations and teams are involved, how confident the system is, and
> optionally a plain-English summary on top. It never takes action on its
> own — it only ever proposes a work note back to ServiceNow, and only
> after a person explicitly approves it.
>
> The correlation itself needs no CMDB — it works off ServiceNow incident
> data that already exists. There's a separate CI Relationships tab that
> *does* read the CMDB, for when you specifically want to see what's
> technically connected to the incident's configuration item — but that's
> an optional, additional view, not something the correlation score
> depends on.

### The leadership version (outcome first, mechanism second)

> Today, figuring out whether one incident is connected to others is
> manual and slow — an analyst has to think to go check. This agent does
> that check in seconds, every time, automatically, the moment an
> incident is opened.
>
> The value isn't a smarter AI guess — it's that the scoring is fully
> deterministic and auditable. Every confidence number can be traced back
> to a fixed formula, not a black box. The AI layer only translates the
> result into plain English; it never decides anything on its own.
>
> And critically: it never closes a ticket, never reprioritizes, never
> declares a major incident by itself. Everything is advisory, and every
> write requires a human to explicitly click confirm. This is a tool that
> makes analysts faster, not one that acts behind their back.
>
> This is also a stepping stone — it's built as a stand-in for a native
> agent on the Blueverse LTM platform. The interface and the report shape
> are kept deliberately independent of this backend, so swapping to the
> platform-native version later is a data-source change, not a rebuild.

### The technical deep-dive (an engineer who wants to see the mechanism)

> Point them at Part 2's table and `correlate.py` directly. The whole
> engine is ~5 weighted signals plus a contradiction-phrase scan; there's
> no hidden state and no model in the loop for scoring. Worth calling out
> specifically:
> - Weights are named constants at the top of `correlate.py`, not tuned
>   magic numbers buried in logic.
> - The "challenge" step (false-positive exclusion) is the part most
>   naive correlation tools skip — it's what keeps confidence honest
>   instead of just counting raw matches.
> - `api.py` has zero business logic — every route is a direct call into
>   `snow_agent`, so the CLI and the UI are provably running the same
>   math, not two implementations that happen to agree today.

---

## Part 4 — A live demo script

The strongest demo mixes a **pre-seeded background** with **one incident
created live**, so it looks real without leaving a clean cluster match
to chance in front of an audience.

**Before the audience arrives**
1. Set credentials, run `python -m snow_agent.seed_incidents` to create
   the background cluster.
2. Have `python api.py` and `npm run dev` already running. Two browser
   tabs open: ServiceNow, and the agent's UI.

**Live**
3. On the ServiceNow tab, create a new incident by hand — short
   description, location, and assignment group matching one of the
   seeded clusters. Narrate it as "a user just called this in."
4. Submit, copy the new incident number.
5. Switch to the agent's UI, paste the number, click **Analyze**.
6. The radial view and confidence score appear live — this ticket was
   created seconds ago and the agent independently found it belongs with
   the earlier ones, purely by scoring, with nothing pre-told.
7. Optional: click **Narrate** for the plain-English summary.
8. Optional: click the **CI Relationships** tab to show the live
   dependency graph pulled from `cmdb_ci`/`cmdb_rel_ci` — run
   `python -m snow_agent.seed_cmdb` beforehand so there's real data to
   show, and set the seeded incident's Configuration Item field to one of
   the seeded CIs (e.g. "Expense Management System") so the tab has
   something to root on.
9. Optional, strongest closer: **Accept** → confirm → it posts a real
   work note to ServiceNow → flip back to the ServiceNow tab, refresh,
   show the note actually sitting there. Proves the write-back is real.

---

## Part 5 — Anticipated hard questions

- **"Does it ever guess?"** — No. Every score is a fixed formula (Part
  2's table); nothing is estimated by an AI model. The optional LLM
  layer only narrates a result that's already computed.
- **"What if it's wrong?"** — It shows a confidence number for exactly
  this reason, and it never acts unilaterally — every ServiceNow write
  requires explicit human confirmation.
- **"Does this replace an analyst?"** — No, it replaces the first
  10–30 minutes of manual searching an analyst would otherwise do by hand.
- **"Is this connected to real data right now?"** — Only if the
  `SERVICENOW_*` environment variables are set; otherwise every entry
  point fails with an honest "not configured" message, never a fake
  answer.
- **"Why not use the CMDB / a dependency graph?"** — The correlation math
  doesn't require one by design; it works off ServiceNow incident data
  that already exists, rather than a graph that has to be built and kept
  up to date. That said, the UI does have a separate "CI Relationships"
  tab that reads the real CMDB (`cmdb_ci`/`cmdb_rel_ci`) when you
  specifically want to see technical dependencies around an incident's
  configuration item — it's an additional view, and it never feeds back
  into the confidence score.
- **"Is this permanent?"** — No — it's a stand-in, expected to be
  replaced by a native agent on the Blueverse LTM platform. The UI and
  report format are kept decoupled from this backend specifically so
  that swap doesn't require rebuilding the interface.

---

## Troubleshooting

- **`error: set SERVICENOW_INSTANCE_URL, ...`** — Part 1, Step 2; none
  of the three ServiceNow variables are optional.
- **Web UI shows "ServiceNow not configured yet"** — same cause,
  surfaced in the UI. Set the env vars where `python api.py` runs, then
  restart it (env vars are only read at startup).
- **Narrate/chat show a credential error** — one of the `AZURE_OPENAI_*`
  variables isn't set. Everything else works without it.
- **Seeded incidents don't form the expected cluster** — `location`/
  `assignment_group` in `seed_incidents.py` may not match real records in
  your instance, so that field got dropped on creation. Edit
  `LOCATIONS`/`GROUPS` in that file to match your instance, or widen
  `--hours`.
- **`npm`/`node` not recognized** — install Node.js from nodejs.org, then
  reopen your terminal.
- **Vite dev server picks a different port than 5173** — something else
  is already using it; use whichever URL it actually prints.
