"""
handler.py — L0 Self-Service
───────────────────────────────
Thin wrapper around retrieval_agent/l0_chat.py's existing chat() function --
answers only from a matched KB card's reviewed self_service block, never
diagnosis/cause (see that module's own docstring). Session/outcome
bookkeeping here mirrors app/routers/l0.py's l0_sessions tracking so the
deflection-rate stat stays correct; ticket creation itself is out of scope
for this agent (that is the Ticket Intake & Creation Agent, #3 on the
roadmap, which is not implemented in this codebase).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent.kb_resolver import fetch_units  # noqa: E402
from retrieval_agent.l0_chat import chat  # noqa: E402
from retrieval_agent.providers import KB_EMBEDDING_DIMENSIONS, Settings, complete_json, embed_texts  # noqa: E402

from l0_self_service_mcp.models import OUTCOMES  # noqa: E402

_MEM: dict[str, dict] = {}  # used only when no Postgres is configured


def _use_pg() -> bool:
    return bool(os.environ.get("PG_HOST")) and os.environ.get("FIX_STORE") != "memory"


def _pg():
    from app.routers.tickets import get_conn
    return get_conn()


def _record(session_id: str | None, outcome: str | None = None, unit_id: str | None = None) -> None:
    if not session_id:
        return
    if not _use_pg():
        row = _MEM.setdefault(session_id, {"outcome": "open", "unit_id": None})
        if outcome and not (row["outcome"] == "ticket_created" and outcome == "resolved"):
            row["outcome"] = outcome
        row["unit_id"] = unit_id or row["unit_id"]
        return
    with _pg() as c:
        c.execute("""INSERT INTO l0_sessions (id, unit_id, outcome) VALUES (%s,%s,COALESCE(%s,'open'))
                     ON CONFLICT (id) DO UPDATE SET unit_id=COALESCE(EXCLUDED.unit_id, l0_sessions.unit_id),
                       outcome=CASE WHEN l0_sessions.outcome='ticket_created' THEN l0_sessions.outcome
                                    ELSE COALESCE(%s, l0_sessions.outcome) END, updated_at=now()""",
                  (session_id, unit_id, outcome, outcome))


def run_l0_chat(messages: list[dict], session_id: str | None) -> dict:
    """
    Answers a requester's chat turn only from a matched KB card's reviewed
    self_service block. Returns module, matched_card, steps, ask_for,
    ticket_draft, verified, resolved_by_bot, reply.
    """
    settings = Settings.load()
    out = chat(
        messages,
        fetch_units(settings),
        settings,
        lambda text: embed_texts(settings, [text], KB_EMBEDDING_DIMENSIONS)[0],
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )
    _record(session_id, unit_id=out.get("unit_id"))
    return out


def record_outcome(session_id: str, outcome: str) -> dict:
    """Records how an L0 chat session ended: open, resolved, or ticket_created."""
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    _record(session_id, outcome=outcome)
    return {"session_id": session_id, "outcome": outcome}


def get_stats() -> dict:
    """Returns chats, resolved_without_ticket, tickets_created, deflection_rate."""
    if not _use_pg():
        rows = list(_MEM.values())
        counts = {o: sum(1 for r in rows if r["outcome"] == o) for o in OUTCOMES}
    else:
        with _pg() as c:
            counts = {o: 0 for o in OUTCOMES}
            for r in c.execute("SELECT outcome, COUNT(*) AS n FROM l0_sessions GROUP BY outcome").fetchall():
                counts[r["outcome"]] = r["n"]
    total = sum(counts.values())
    return {
        "chats": total,
        "resolved_without_ticket": counts["resolved"],
        "tickets_created": counts["ticket_created"],
        "deflection_rate": round(100 * counts["resolved"] / total) if total else 0,
    }
