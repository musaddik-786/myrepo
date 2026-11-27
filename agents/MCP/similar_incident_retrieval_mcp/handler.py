"""
handler.py — Similar Incident Retrieval
──────────────────────────────────────────
Thin wrapper around retrieval_agent/pipeline.py's existing retrieve()
function and the same ticket-detail enrichment already used by
app/routers/similar.py for the UI -- no ranking/matching logic lives here.
Operates over ticket_records (real historical tickets), not the 13 KB
cards (see kb_matching_mcp for that).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent.database import fetch_eligible_tickets  # noqa: E402
from retrieval_agent.pipeline import retrieve  # noqa: E402
from retrieval_agent.providers import Settings, complete_json, embed_texts  # noqa: E402


def _detail(record: dict[str, Any]) -> dict[str, Any]:
    meta = record.get("source_metadata") or {}
    return {
        "description": record.get("description"),
        "system": record.get("system"),
        "created": str(record["created"]) if record.get("created") else None,
        "closed": str(record["closed"]) if record.get("closed") else None,
        "severity": record.get("severity"),
        "resolution": record.get("resolution"),
        "rca": record.get("rca"),
        "runbook_link": record.get("runbook_link"),
        "assignee_team": meta.get("assignee_team"),
    }


def find_similar_incidents(
    id: str | None,
    title: str | None,
    description: str | None,
    module: str | None,
    severity: str | None,
    created: str | None,
) -> dict:
    """
    Finds past resolved tickets similar to the given one, always runs
    (never blocked by whether a KB card exists). Returns new_ticket_assessment,
    matches (each enriched with a `ticket` detail block), no_confident_match,
    and suggested_next_step.
    """
    settings = Settings.load()
    ticket = {
        "id": id,
        "short_description": title,
        "description": description,
        "system": module,
        "severity": severity,
        "created": created,
    }
    ticket = {k: v for k, v in ticket.items() if v}

    records = fetch_eligible_tickets(settings)
    if id:  # a ticket must not match itself
        records = [r for r in records if r["ticket_id"].casefold() != id.casefold()]

    result = retrieve(
        ticket, records, settings,
        lambda text: embed_texts(settings, [text])[0],
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )

    by_id = {r["ticket_id"]: r for r in records}
    for match in result.get("matches", []):
        match["ticket"] = _detail(by_id.get(match["id"], {}))

    return result
