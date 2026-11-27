"""L0 self-service: /chat answers from reviewed self-service text, /ticket raises an osTicket ticket, /stats feeds the dashboard."""
import os
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from psycopg import Error as PsycopgError

from app.services.osticket_create import TicketCreateError, create_ticket
from retrieval_agent.kb_resolver import fetch_units
from retrieval_agent.l0_chat import chat
from retrieval_agent.providers import KB_EMBEDDING_DIMENSIONS, Settings, complete_json, embed_texts

router = APIRouter(prefix="/api/l0")
OUTCOMES = ("open", "resolved", "ticket_created")
_MEM: dict[str, dict] = {}   # used only when no Postgres is configured (or FIX_STORE=memory)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    session_id: str | None = None


class OutcomeRequest(BaseModel):
    session_id: str
    outcome: str


class TicketRequest(BaseModel):
    session_id: str | None = None
    name: str
    email: str
    title: str
    description: str
    module: str | None = None


def _pg() -> bool:
    return bool(os.environ.get("PG_HOST")) and os.environ.get("FIX_STORE") != "memory"


def _conn():
    from app.routers.tickets import get_conn
    return get_conn()


def record(session_id: str | None, outcome: str | None = None, unit_id: str | None = None, ref: str | None = None) -> None:
    if not session_id:
        return
    if not _pg():
        row = _MEM.setdefault(session_id, {"outcome": "open", "unit_id": None, "ticket_ref": None})
        if outcome and not (row["outcome"] == "ticket_created" and outcome == "resolved"):
            row["outcome"] = outcome
        row["unit_id"] = unit_id or row["unit_id"]
        row["ticket_ref"] = ref or row["ticket_ref"]
        return
    with _conn() as c:
        c.execute("""INSERT INTO l0_sessions (id, unit_id, outcome, ticket_ref) VALUES (%s,%s,COALESCE(%s,'open'),%s)
                     ON CONFLICT (id) DO UPDATE SET unit_id=COALESCE(EXCLUDED.unit_id, l0_sessions.unit_id),
                       outcome=CASE WHEN l0_sessions.outcome='ticket_created' THEN l0_sessions.outcome
                                    ELSE COALESCE(%s, l0_sessions.outcome) END,
                       ticket_ref=COALESCE(EXCLUDED.ticket_ref, l0_sessions.ticket_ref), updated_at=now()""",
                  (session_id, unit_id, outcome, ref, outcome))


@router.post("/chat")
def l0_chat(req: ChatRequest) -> dict[str, Any]:
    settings = Settings.load()
    try:
        out = chat([m.model_dump() for m in req.messages], fetch_units(settings), settings,
                   lambda t: embed_texts(settings, [t], KB_EMBEDDING_DIMENSIONS)[0], lambda s, u: complete_json(settings, s, u))
        record(req.session_id, unit_id=out.get("unit_id"))
        return out
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except PsycopgError as exc:
        raise HTTPException(503, f"Database query failed: {exc}") from exc


@router.post("/outcome")
def l0_outcome(req: OutcomeRequest) -> dict:
    if req.outcome not in OUTCOMES:
        raise HTTPException(422, f"outcome must be one of {OUTCOMES}")
    record(req.session_id, outcome=req.outcome)
    return {"ok": True}


@router.post("/ticket")
def l0_ticket(req: TicketRequest) -> dict:
    if not (req.name.strip() and req.email.strip() and req.title.strip()):
        raise HTTPException(422, "Name, email and a title are required.")
    try:
        number = create_ticket(req.name.strip(), req.email.strip(), req.title.strip()[:200], req.description, req.module)
    except TicketCreateError as exc:
        raise HTTPException(502, str(exc)) from exc
    record(req.session_id, outcome="ticket_created", ref=number)
    return {"ticket_number": number}


@router.get("/stats")
def l0_stats() -> dict:
    if not _pg():
        rows = list(_MEM.values())
        counts = {o: sum(1 for r in rows if r["outcome"] == o) for o in OUTCOMES}
    else:
        with _conn() as c:
            counts = {o: 0 for o in OUTCOMES}
            for r in c.execute("SELECT outcome, COUNT(*) AS n FROM l0_sessions GROUP BY outcome").fetchall():
                counts[r["outcome"]] = r["n"]
    total = sum(counts.values())
    return {"chats": total, "resolved_without_ticket": counts["resolved"], "tickets_created": counts["ticket_created"],
            "deflection_rate": round(100 * counts["resolved"] / total) if total else 0}
