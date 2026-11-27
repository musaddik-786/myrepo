"""
handler.py — Knowledge Ingestion & Curation
────────────────────────────────────────────
Two unrelated jobs live here, on purpose kept apart:

run_ingestion -- a thin wrapper around backend/pipeline.py's existing,
already-working BATCH refresh (ingest -> structure/embed -> SME curation
gate -> Knowledge Store), sourced from the static data/raw/*.json files.
No ingestion/tagging/curation logic lives here -- this only adapts
backend.pipeline.run_pipeline() to a request/response contract and captures
its stdout progress log, since that function reports progress by printing
rather than returning a value. This has NOTHING to do with the live,
osTicket-synced ticket_records table -- see ingest_closed_ticket below for
that.

ingest_closed_ticket -- the exact same single-ticket embed logic as
app/routers/fix.py's _store_resolution(), just exposed as this agent's MCP
tool instead of living inline there. This is what the orchestrator agent
calls on "Close ticket and save to knowledge" for a real, live ticket --
run_ingestion's data/raw/tickets.json source never sees that ticket at all.
"""
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_DIR = _ROOT / "backend"
for _p in (str(_ROOT), str(_BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.pipeline import run_pipeline  # noqa: E402
from backend.taxonomy import SourceType  # noqa: E402

from knowledge_ingestion_curation_mcp.models import VALID_SOURCES  # noqa: E402

_SOURCE_KEY_TO_TYPE: dict[str, SourceType] = {
    "tickets": SourceType.TICKET,
    "chat_rca": SourceType.CHAT_RCA,
    "release_notes": SourceType.RELEASE_NOTE,
    "runbooks": SourceType.RUNBOOK,
}


def run_ingestion(sources: list[str] | None, force: bool) -> dict:
    """
    Refreshes the Knowledge Store from one or more raw sources (tickets,
    chat_rca, release_notes, runbooks): ingest -> structure/embed ->
    SME curation gate. Omit `sources` to refresh all 4.

    Returns completed (bool), db_connected (bool -- False if Postgres was
    unreachable; stages 1-3 still ran), and log (the pipeline's own
    stage-by-stage stdout).
    """
    if sources is not None:
        unknown = set(sources) - VALID_SOURCES
        if unknown:
            raise ValueError(f"Unknown source(s): {', '.join(sorted(unknown))}. Valid: {sorted(VALID_SOURCES)}")
        mapped_sources = [_SOURCE_KEY_TO_TYPE[s] for s in sources]
    else:
        mapped_sources = None

    buffer = io.StringIO()
    db_connected = True
    try:
        with redirect_stdout(buffer):
            run_pipeline(sources=mapped_sources, force=force)
    except SystemExit:
        # run_pipeline() itself calls sys.exit(0) when Postgres is unreachable,
        # after stages 1-3 (ingest/structure/curate) still ran and printed
        # their results -- caught here so this MCP process stays up; not a
        # modification of backend/pipeline.py's own behavior.
        db_connected = False

    return {"completed": True, "db_connected": db_connected, "log": buffer.getvalue()}


def ingest_closed_ticket(ticket_id: str, resolution_type: str, notes: str) -> dict:
    """
    Writes a closed ticket's resolution to its live ticket_records row
    (matched by source_ref_id=ticket_id) and embeds title+description+
    resolution so it becomes findable by Similar Incident Retrieval. Returns
    ticket_store=False, embedded=False if no such row exists (nothing to do).

    Byte-for-byte the same logic as app/routers/fix.py's _store_resolution(),
    moved here so it is this agent's MCP tool rather than inline app code.
    """
    from app.routers.tickets import get_conn
    from retrieval_agent.database import _vector_text
    from retrieval_agent.providers import Settings, embed_texts

    with get_conn() as c:
        row = c.execute(
            """UPDATE ticket_records SET resolution=%s, resolution_type=%s,
               curation_status='SMEApproved', upserted_at=now()
               WHERE source_ref_id=%s RETURNING record_id, title, raw_text""",
            (notes, resolution_type, ticket_id),
        ).fetchone()
        if not row:
            return {"ticket_store": False, "embedded": False}
        try:
            settings = Settings.load()
            text = f"{row['title']} {row['raw_text']} {notes}"[:6000]
            vec = embed_texts(settings, [text])[0]
            c.execute(
                "UPDATE ticket_records SET embedding=%s::vector WHERE record_id=%s",
                (_vector_text(vec), row["record_id"]),
            )
            return {"ticket_store": True, "embedded": True}
        except Exception as exc:  # resolution is saved even if the embedding service is down
            return {"ticket_store": True, "embedded": False, "embed_error": type(exc).__name__}
