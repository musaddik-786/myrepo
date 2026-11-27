"""L1/L2/L3 fix workflow: run a stage, approve or reject the L3 output, export the requirement document."""
import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from retrieval_agent import fix_steps, requirement_doc
from retrieval_agent.kb_resolver import fetch_units, resolve
from retrieval_agent.providers import KB_EMBEDDING_DIMENSIONS, Settings, complete_json, embed_texts

router = APIRouter(prefix="/api/fix")
STAGES = ("l1", "l2", "l3")
_MEM: dict[str, dict] = {}      # used only when no Postgres is configured (local demo, tests)
_MEM_AUDIT: list[dict] = []


class RunRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    user: str = "analyst"


class DecisionRequest(BaseModel):
    approver: str
    change_id: str = ""
    note: str = ""


RESOLUTION_TYPES = ("ConfigChange", "CodeFix", "PatchApplied", "RestartRecycle", "DataRemediation",
                    "VendorEscalation", "Workaround", "UserErrorClosed", "NoActionByDesign")


class ResolveRequest(BaseModel):
    level: str                      # l1 | l2 | l3: which workbench step resolved the ticket
    resolution_type: str
    notes: str
    resolved_by: str


def _pg():
    from app.routers.tickets import get_conn
    return get_conn()


def _use_pg() -> bool:
    return bool(os.environ.get("PG_HOST")) and os.environ.get("FIX_STORE") != "memory"


def load_run(ticket_id: str) -> dict:
    blank = {"ticket_id": ticket_id, "stage": "new", "status": "open", "outputs": {}, "run_by": None}
    if not _use_pg():
        return _MEM.get(ticket_id, blank)
    with _pg() as c:
        row = c.execute("SELECT ticket_id, stage, status, outputs, run_by FROM fix_runs WHERE ticket_id=%s",
                        (ticket_id,)).fetchone()
    return row or blank


def save_run(run: dict) -> None:
    if not _use_pg():
        _MEM[run["ticket_id"]] = run
        return
    with _pg() as c:
        c.execute("""INSERT INTO fix_runs (ticket_id, stage, status, outputs, run_by) VALUES (%s,%s,%s,%s::jsonb,%s)
                     ON CONFLICT (ticket_id) DO UPDATE SET stage=EXCLUDED.stage, status=EXCLUDED.status,
                     outputs=EXCLUDED.outputs, run_by=EXCLUDED.run_by, updated_at=now()""",
                  (run["ticket_id"], run["stage"], run["status"], json.dumps(run["outputs"]), run["run_by"]))


def audit(ticket_id: str, action: str, actor: str, detail: dict) -> None:
    if not _use_pg():
        _MEM_AUDIT.append({"ticket_id": ticket_id, "action": action, "actor": actor, "detail": detail})
        return
    with _pg() as c:
        c.execute("INSERT INTO fix_audit_log (ticket_id, action, actor, detail) VALUES (%s,%s,%s,%s::jsonb)",
                  (ticket_id, action, actor, json.dumps(detail)))


def _complete(settings):
    return lambda s, u: complete_json(settings, s, u)


def _match_card(ticket: dict, settings) -> dict:
    res = resolve(ticket, fetch_units(settings), settings, lambda t: embed_texts(settings, [t], KB_EMBEDDING_DIMENSIONS)[0], _complete(settings))
    if not res.get("matched") or not res.get("unit"):
        raise HTTPException(409, "No knowledge card matches this ticket, so there is nothing to guide or diagnose.")
    return res["unit"]["content"]


def _card_of(run: dict) -> dict:
    card = run["outputs"].get("card")
    if not card:
        raise HTTPException(409, "Run L1 first.")
    return card


@router.post("/{ticket_id}/run/{stage}")
def run_stage(ticket_id: str, stage: str, req: RunRequest) -> dict[str, Any]:
    if stage not in STAGES:
        raise HTTPException(404, "Stage must be l1, l2 or l3")
    ticket = {"title": req.title, "description": req.description}
    run = load_run(ticket_id)
    if run["status"] == "closed":
        raise HTTPException(409, "This ticket is closed.")
    out, source = run["outputs"], "ai"
    try:
        settings = Settings.load()
        complete = _complete(settings)
        if stage == "l1":
            card = _match_card(ticket, settings)
            out.update(card=card, l1=fix_steps.l1_guide(ticket, card, complete))
        else:
            card = _card_of(run)
            evidence = fix_steps.load_evidence(card["unit_id"])
            if not evidence:
                raise HTTPException(409, f"No sample evidence is available for {card['unit_id']} in this demo.")
            if stage == "l2":
                out["l2"] = fix_steps.l2_diagnose(ticket, card, evidence, complete)
            else:
                if "l2" not in out:
                    raise HTTPException(409, "Run L2 first.")
                if not out["l2"].get("needs_data_fix"):
                    raise HTTPException(409, "L2 found no data fix is needed.")
                out["l3"] = fix_steps.l3_author(ticket_id, ticket, card, out["l2"], evidence, complete)
    except RuntimeError as exc:           # AI service unreachable: use the saved sample if one exists
        fb = _fallback(stage, run, ticket_id, ticket)
        if fb is None:
            raise HTTPException(502, str(exc)) from exc
        out.update(fb)
        source = "saved-sample"
    run.update(stage=stage, status="open", outputs=out, run_by=req.user if stage == "l3" else run.get("run_by"))
    save_run(run)
    audit(ticket_id, "stage_run", req.user, {"stage": stage, "source": source})
    return {"ticket_id": ticket_id, "stage": stage, "source": source, **{k: out.get(k) for k in ("card", stage)}}


def _fallback(stage: str, run: dict, ticket_id: str, ticket: dict) -> dict | None:
    card = run["outputs"].get("card")
    uid = (card or {}).get("unit_id") or "PC-AUD-01"
    fb, ev = fix_steps.load_fallback(uid), fix_steps.load_evidence(uid)
    if not fb or not ev or uid != "PC-AUD-01":
        return None
    if stage == "l1":
        units = [json.loads(p.read_text()) for p in (fix_steps.DEMO_DIR.parents[0] / "units").glob("PC-AUD-01.json")]
        c = units[0]
        items = [{"item": t, "answered": False, "found": ""} for t in c["info_to_collect"]]
        return {"card": c, "l1": {"items": items, "missing_count": len(items), "requester_reply": "",
                                   "escalation": c["escalation"]}}
    if stage == "l2":
        bad = set(fb["l2"]["ok_false"])
        checks = [{"id": c["id"], "what": c["description"], "query": c["query"], "found": c["result"],
                   "facts": c.get("facts", {}), "ok": c["id"] not in bad} for c in ev["checks"]]
        return {"l2": {"checks": checks, "conclusion": fb["l2"]["conclusion"], "needs_data_fix": True,
                       "confidence": "high", "evidence_label": ev["_label"]}}
    l3 = dict(fb["l3"])
    l3["gosu"] = l3["gosu"].replace("{ticket_id}", str(ticket_id))
    from retrieval_agent import gosu_guard
    l3["guard"] = gosu_guard.check(l3["gosu"], ticket_id, ev["policy_number"])
    l3["repairs"] = 0
    l3["requirement"] = requirement_doc.validate({**l3["requirement"], "linked_tickets": card["related_tickets"],
                                                  "source_ticket": str(ticket_id), "source_card": card["article_id"]})
    return {"l3": l3}


@router.get("/audit")
def audit_trail(limit: int = 100) -> list[dict]:
    if not _use_pg():
        return list(reversed(_MEM_AUDIT))[:limit]
    with _pg() as c:
        return c.execute("SELECT ticket_id, action, actor, detail, created_at FROM fix_audit_log "
                         "ORDER BY created_at DESC LIMIT %s", (limit,)).fetchall()


@router.get("/{ticket_id}")
def get_run(ticket_id: str) -> dict:
    return load_run(ticket_id)


def _decide(ticket_id: str, req: DecisionRequest, approve: bool) -> dict:
    run = load_run(ticket_id)
    l3 = run["outputs"].get("l3")
    if not l3:
        raise HTTPException(409, "Nothing to decide: L3 has not run.")
    if run["status"] in ("approved", "rejected", "closed"):
        raise HTTPException(409, f"Already {run['status']}.")
    if not req.approver.strip():
        raise HTTPException(422, "Approver is required.")
    if approve:
        if req.approver.strip().lower() == (run.get("run_by") or "").strip().lower():
            raise HTTPException(403, "The approver cannot be the person who ran L3.")
        if not l3["guard"]["passed"]:
            raise HTTPException(409, "The script failed the safety checks and cannot be approved.")
        if not req.change_id.strip():
            raise HTTPException(422, "A change-control id is required to approve.")
    run["status"] = "approved" if approve else "rejected"
    run["stage"] = run["status"]
    run["outputs"]["decision"] = {"approver": req.approver, "change_id": req.change_id, "note": req.note,
                                  "script_sha256": hashlib.sha256(l3["gosu"].encode()).hexdigest()}
    save_run(run)
    audit(ticket_id, run["status"], req.approver, run["outputs"]["decision"])
    return run


@router.post("/{ticket_id}/approve")
def approve(ticket_id: str, req: DecisionRequest) -> dict:
    return _decide(ticket_id, req, True)


@router.post("/{ticket_id}/reject")
def reject(ticket_id: str, req: DecisionRequest) -> dict:
    return _decide(ticket_id, req, False)


def _store_resolution(ticket_id: str, rtype: str, notes: str) -> dict:
    """Write the resolution to ticket_records and embed title + description + resolution so it can be found later."""
    if not _use_pg():
        return {"ticket_store": False, "embedded": False}
    from retrieval_agent.database import _vector_text
    with _pg() as c:
        row = c.execute("""UPDATE ticket_records SET resolution=%s, resolution_type=%s,
                           curation_status='SMEApproved', upserted_at=now()
                           WHERE source_ref_id=%s RETURNING record_id, title, raw_text""",
                        (notes, rtype, ticket_id)).fetchone()
        if not row:
            return {"ticket_store": False, "embedded": False}
        try:
            settings = Settings.load()
            text = f"{row['title']} {row['raw_text']} {notes}"[:6000]
            vec = embed_texts(settings, [text])[0]
            c.execute("UPDATE ticket_records SET embedding=%s::vector WHERE record_id=%s",
                      (_vector_text(vec), row["record_id"]))
            return {"ticket_store": True, "embedded": True}
        except Exception as exc:  # resolution is saved even if the embedding service is down
            return {"ticket_store": True, "embedded": False, "embed_error": type(exc).__name__}


@router.post("/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, req: ResolveRequest) -> dict:
    run = load_run(ticket_id)
    if req.level not in STAGES or req.level not in run["outputs"]:
        raise HTTPException(409, f"Run {req.level.upper()} before resolving with it.")
    if run["status"] == "closed":
        raise HTTPException(409, "Already closed.")
    if req.resolution_type not in RESOLUTION_TYPES:
        raise HTTPException(422, "Unknown resolution type.")
    if not req.notes.strip() or not req.resolved_by.strip():
        raise HTTPException(422, "Resolution notes and your name are required.")
    if req.level == "l3" and run["status"] != "approved":
        raise HTTPException(409, "The L3 fix must be approved before the ticket can be closed with it.")
    try:
        stored = _store_resolution(ticket_id, req.resolution_type, req.notes.strip())
    except Exception as exc:
        raise HTTPException(503, f"Could not save the resolution: {type(exc).__name__}") from exc
    run["outputs"]["resolution"] = {"level": req.level, "resolution_type": req.resolution_type,
                                    "notes": req.notes.strip(), "resolved_by": req.resolved_by.strip(), **stored}
    run["status"], run["stage"] = "closed", "closed"
    save_run(run)
    audit(ticket_id, "closed", req.resolved_by.strip(), run["outputs"]["resolution"])
    return run


def _requirement(ticket_id: str) -> dict:
    l3 = load_run(ticket_id)["outputs"].get("l3")
    if not l3 or "error" in (l3.get("requirement") or {"error": 1}):
        raise HTTPException(404, "No requirement document for this ticket yet.")
    return l3["requirement"]


@router.get("/{ticket_id}/requirement.json")
def requirement_json(ticket_id: str) -> dict:
    return _requirement(ticket_id)


@router.get("/{ticket_id}/requirement.md", response_class=PlainTextResponse)
def requirement_md(ticket_id: str) -> str:
    return requirement_doc.to_markdown(_requirement(ticket_id))
