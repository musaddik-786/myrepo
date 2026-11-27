# Introduction 
TODO: Give a short introduction of your project. Let this section explain the objectives or the motivation behind this project. 

# Getting Started
TODO: Guide users through getting your code up and running on their own system. In this section you can talk about:
1.	Installation process
2.	Software dependencies
3.	Latest releases
4.	API references

# Build and Test
TODO: Describe and show how to build your code and run the tests. 

# Contribute
TODO: Explain how other users and developers can contribute to make your code better. 

If you want to learn more about creating good readme files then refer the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)

# Project structure (consolidated)
```
app/              single FastAPI entrypoint (serves /api/*, /retrieve, /health and built UI at /)
backend/          KB pipeline (ingestion, structuring, curation, store) - run from inside backend/
retrieval_agent/  similar-ticket retrieval (hybrid BM25 + vectors + LLM rerank)
ui/               React UI (Vite); ui/server_legacy_express = old Node API, replaced by app/routers/tickets.py
db/               schema.sql (vector(1536)), create_new_db.py, migrations/
data/raw          merged source JSON; data/archive/kavita = original Kavita inputs (xlsx, json, 512-dim schema)
tests/            pytest suite
```

# Run
```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp sample.env .env            # then fill values (a populated .env is git-ignored)
python db/create_new_db.py --dry-run   # shows names; drop --dry-run to create <db>_1536 (existing DB untouched)
# point PG_DATABASE / AZURE_PG_DATABASE in .env at the new DB, then:
cd backend && python step3_populate_data.py && python step4_store_embeddings.py && cd ..
psql -f db/migrations/002_vector_indexes.sql      # optional HNSW indexes, after embeddings exist
cd ui && npm ci && npm run build && cd ..
uvicorn app.main:app --port 7000                  # UI at http://localhost:7000/
pytest tests && python -m unittest retrieval_agent.tests
```
This starts the main app only. Every AI action in the UI (Classify, L1/L2/L3, Approve, Resolve, self-service chat) also needs the shared MCP server and the relevant agent process(es) running -- see "Agents" below.

Azure App Service (Linux, Python 3.11): startup command `bash startup.sh`; set `.env` keys as app settings; deploy repo with built `ui/dist`.

# Similar historical tickets
Served by the real, standalone Similar Incident Retrieval Agent (`agents/similar_incident_retrieval`, port 7013) -- its `find_similar_incidents` tool runs the retrieval agent (hybrid BM25 + vector + LLM rerank) and returns ranked matches, each enriched with the matched ticket's description, system, resolution and RCA, plus `no_confident_match` and `suggested_next_step`. A ticket never matches its own ID. It searches the single ticket store, `ticket_records` (approved tickets whose embeddings match `EMBEDDING_DIMENSIONS`, default 3072, created by `backend/step3` + `step4`).
In the UI the "Similar historical tickets" panel does **not** load automatically -- it only runs when its own "Find similar tickets" button is clicked (`POST /api/orchestrator/similar/{ticket_id}`, a direct call to the agent above, independent of the Orchestrator Agent's L1/L2/L3 flow), or when the Orchestrator Agent's own L1 run calls this same agent as one of its steps. Either way the result is persisted into the ticket's `fix_runs.outputs.similar`, so the panel shows the same thing regardless of which path produced it. See "Agents" below for how to start it.

# osTicket integration (source of truth for tickets)
osTicket is the ITSM system where tickets are created and worked. This app is the **AI Insights** layer on top: tagging, similar tickets, SOPs and curation. Users create tickets in osTicket (the UI's "New Ticket" button opens osTicket's `/open.php`); each ticket row in the UI links back to its osTicket page.

**How it works.** `app/services/osticket.py` reads tickets from osTicket and upserts them into `ticket_records` (`record_id = osticket-<ticket_id>`, `source_ref_id` = osTicket ticket number, `source_url` = link to the ticket).
- Updates in osTicket (title, body, priority, status, team, closed date) are refreshed on every sync. AI tagging and curation fields are never overwritten.
- Tickets deleted in osTicket are soft-flagged (`source_metadata.removed = true`) and hidden from the UI list and retrieval; a ticket that reappears is un-flagged. The removal step is skipped if osTicket returns zero tickets.
- Synced rows start as `NeedsRetag` with confidence 0 and placeholder `module`/`category` (the table requires them) until the AI tagger runs.
- osTicket's core HTTP API is create-only (`POST /api/tickets.json`, `POST /api/tasks/cron`), so the sync reads osTicket's MySQL database through a **read-only** user. A webhook plugin or the Extended API plugin would remove that dependency.

**Severity** values are `Low`, `Normal`, `High`, `Emergency` everywhere (existing databases need `db/migrations/2026-11-17_osticket_severity.sql` applied once -- converts old `SEV1-Critical`..`SEV4-Low` values and the CHECK constraints on all four record tables). A freshly-synced osTicket row gets a fixed placeholder severity (`Normal`, same idea as its placeholder `module`/`category`) -- it is **not** derived from osTicket's own priority field, so nothing shown before classification can be mistaken for the Ticket Classification & Triage Agent's real output. The agent (not osTicket) decides the real severity once Classify runs; osTicket's actual priority is kept separately in `source_metadata.priority`. See `app/services/osticket.py`.

**Backend config** (see `sample.env`):
| Variable | Purpose |
|---|---|
| `OSTICKET_URL` | osTicket base URL, used to build per-ticket links |
| `OSTICKET_DB_HOST/PORT/NAME` | osTicket MySQL (default `127.0.0.1:3306`, db `osticket`) |
| `OSTICKET_DB_USER/PASSWORD` | a **read-only** MySQL user (`GRANT SELECT` only) |
| `OSTICKET_SYNC_INTERVAL` | seconds between automatic syncs; leave empty for manual only |

UI: set `VITE_OSTICKET_URL` (defaults to `http://127.0.0.1:8081`) for the New Ticket link.

**Run a sync**
```bash
python -m app.services.osticket --dry-run     # show what would sync, writes nothing
curl -X POST localhost:7000/api/osticket/sync # run it (add ?dry_run=true to preview)
curl localhost:7000/api/osticket/status       # is the DB configured?
```

**Run osTicket locally without Docker** (Debian/Ubuntu; for development only, use a proper web server in production)
```bash
sudo apt-get install -y mariadb-server php-cli php-mysql php-mbstring php-xml php-gd php-intl php-apcu php-imap php-curl php-zip
sudo mysql -e "CREATE DATABASE osticket CHARACTER SET utf8mb4;
  CREATE USER 'osticket'@'localhost' IDENTIFIED BY '<pw>'; GRANT ALL ON osticket.* TO 'osticket'@'localhost';
  CREATE USER 'osticket_ro'@'localhost' IDENTIFIED BY '<ro-pw>'; GRANT SELECT ON osticket.* TO 'osticket_ro'@'localhost';"
# download osTicket v1.18.x from https://github.com/osTicket/osTicket/releases, unzip, copy upload/ to ~/osticket
cp ~/osticket/include/ost-sampleconfig.php ~/osticket/include/ost-config.php && chmod 666 ~/osticket/include/ost-config.php
PHP_CLI_SERVER_WORKERS=4 php -d sendmail_path=/bin/true -S 127.0.0.1:8081 -t ~/osticket   # then open http://127.0.0.1:8081/setup/ and run the installer
# after install: chmod 644 include/ost-config.php and remove/move the setup/ folder
```
Dev-server notes: the `sendmail_path=/bin/true` flag stops osTicket's alert emails from failing on machines with no `sendmail` (which left the "Please Wait" popup hanging after creating a ticket); the workers flag stops one slow request blocking the others. PHP's built-in server reports `cli-server`, which makes osTicket's API read stdin instead of the request body, so `POST /api/tickets.json` needs a local patch (`include/class.api.php` constructor: `$this->sapi = $sapi ?: 'http';`) plus a router script mapping `/api/*` to `api/http.php`. Use Apache/nginx + PHP-FPM to avoid both. osTicket's default ban list blocks `test@example.com`. The osTicket install lives outside this repo and is not committed.

**Create the taxonomy in osTicket** (module topics and the category list). Names come from `backend/taxonomy.py`, so they cannot drift from the AI app. Needs `php` and filesystem access to the osTicket install; safe to re-run (existing items are left alone).
```bash
python scripts/osticket_setup_taxonomy.py --dry-run     # preview
python scripts/osticket_setup_taxonomy.py --osticket-dir ~/osticket
```
It creates, via osTicket's own PHP classes (`scripts/osticket/setup_taxonomy.php`): 8 help topics (one per module, e.g. `PolicyCenter`, each linked to the Ticket Details form so the Issue Summary / Details fields appear when it is selected), an `Issue Category` custom list with the 9 categories, and an agent-only `Issue Category` dropdown on the Ticket Details form (requesters pick the module; agents/AI set the category). It also rebuilds osTicket's `ost_ticket__cdata` table so the new column is queryable. osTicket's stock topics (General Inquiry, Feedback, Report a Problem) are left in place; disable them in the admin panel if you only want module topics.

**Mapping osTicket to the taxonomy.** osTicket has no ticket category/sub-category. Plan: help topic = module (8), a custom dropdown list field on the ticket form = category (9), osTicket priority kept as `source_metadata.priority` (not used as severity -- see "Severity" above), osTicket teams = assignee team. The sync maps a help topic to `module` when its name matches a module exactly; it does not read the `Issue Category` field yet, so category still comes from the AI tagger.

## Agents (LangGraph + MCP)
Every AI action in the UI -- Classify, "Find similar tickets", Run L1 guide, L2 diagnosis, L3 data fix, Approve/Reject, Resolve & close, and the self-service chat -- is real agent code (each domain agent's own `handler.py` wrapping the underlying business logic), served through one shared MCP server, never in-process backend code.

**To actually run the UI, only three processes need to be started** (plus the main app and osTicket):
```bash
cd agents/MCP && python main.py          # port 7900 -- hosts every agent's tool code; start this first
cd agents/orchestrator && python server.py    # port 7021 -- decides which tool(s) to call for L1/L2/L3
cd agents/l0_self_service && python server.py # port 7014 -- the self-service chat page's own agent process
```
Classify / "Find similar tickets" / Approve / Reject / Resolve are deterministic, single-tool actions -- there is nothing for an LLM to decide, so `app/routers/orchestrator.py` calls the MCP server directly over HTTP for these, never touching a standalone agent process. L1/L2/L3 and the self-service chat are different: they genuinely need an LLM to decide what to do, so the UI calls a real LangGraph agent's own `/chat` endpoint instead (proxied by the UI dev server -- `ui/vite.config.ts`: `/orchestrator-agent` -> 7021, `/l0-agent` -> 7014); that agent process is itself an MCP client calling back into the same shared MCP server for its tool(s).

**The other 9 agents below also have a real, working standalone `python server.py`** (useful to run and test a single agent/tool in isolation), **but nothing in the UI or main app calls their process or port** -- their actual tool code already runs inside the shared MCP server above, so they are not required to be running for the UI to work:

| Agent | Folder | Port (if run standalone) | Tool it provides |
|---|---|---|---|
| Ticket Classification & Triage | `agents/ticket_classification_triage` | 7020 | Classify |
| KB Matching | `agents/kb_matching` | 7012 | L1 step: matches a ticket to a KB card |
| Similar Incident Retrieval | `agents/similar_incident_retrieval` | 7013 | "Find similar tickets" button, and the L1 step |
| L1 Information Collector | `agents/l1_information_collector` | 7015 | L1 guided-steps checklist |
| PolicyCenter Evidence Collector | `agents/policycenter_evidence_collector` | 7016 | L1's PolicyCenter evidence |
| L2 Diagnostic | `agents/l2_diagnostic` | 7017 | L2 diagnosis |
| L3 Remediation Proposal | `agents/l3_remediation_proposal` | 7018 | L3 Gosu fix + change requirement |
| Human Approval | `agents/human_approval` | 7019 | Approve / Reject |
| Knowledge Ingestion & Curation | `agents/knowledge_ingestion_curation` | 7011 | Resolve & close ticket (saves to knowledge) |

## L0 to L3 resolution workflow (demo)
Ticket workbench (L1 guided steps, L2 diagnosis, L3 Gosu data fix plus change requirement, human approval), L0 self-service chat and an audit trail -- see "Agents" above for the real processes behind each step. `app/routers/fix.py`/`app/routers/l0.py` hold shared persistence helpers (`fix_runs`/`fix_audit_log`/`l0_sessions`) and legacy in-process routes kept for reference but no longer called by the UI; the agent business logic itself lives in `retrieval_agent/fix_steps.py`, `gosu_guard.py`, `requirement_doc.py`, `l0_chat.py`, wrapped by each agent's MCP handler. L2 uses labelled sample evidence in `knowledge/demo/`; Gosu is generated and checked but never executed. First run `python scripts/reset_demo.py <ticket> --migrate` (writes to the Postgres in `.env`); set `FIX_STORE=memory` to run without it. Walk-through: `docs/demo-script.md`.
L0 "Create ticket" runs `scripts/osticket/create_ticket.php` through `php`, so it needs the osTicket files on the same machine (`OSTICKET_DIR`, default `~/osticket`). The dashboard tile counts chats marked "solved without a ticket" in `l0_sessions`.
