"""L1 guide, L2 diagnose, L3 author. Each takes an injected `complete(system, user) -> dict` so tests can stub the LLM."""
import json
from pathlib import Path

from retrieval_agent import gosu_guard, requirement_doc

DEMO_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "demo"
MAX_REPAIRS = 1


def load_evidence(unit_id: str) -> dict | None:
    f = DEMO_DIR / f"{unit_id}_evidence.json"
    return json.loads(f.read_text()) if f.is_file() else None


def load_fallback(unit_id: str) -> dict | None:
    f = DEMO_DIR / f"{unit_id}_fallback.json"
    return json.loads(f.read_text()) if f.is_file() else None


def _ticket_block(ticket: dict) -> str:
    return f"Title: {ticket.get('title') or ''}\nDescription: {ticket.get('description') or ''}"


def l1_guide(ticket: dict, card: dict, complete) -> dict:
    items = list(card.get("info_to_collect") or [])
    system = ("You help an L1 support analyst. For each numbered item, say whether the ticket text already answers it. "
              'Reply JSON: {"items":[{"index":0,"answered":true|false,"found":"short quote or empty"}]}')
    user = _ticket_block(ticket) + "\n\nItems:\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(items))
    got = {r.get("index"): r for r in (complete(system, user).get("items") or []) if isinstance(r, dict)}
    out = []
    for i, text in enumerate(items):
        r = got.get(i, {})
        out.append({"item": text, "answered": bool(r.get("answered")), "found": str(r.get("found") or "")})
    missing = [x["item"] for x in out if not x["answered"]]
    reply = ("Hello, to investigate your request we still need: " + "; ".join(missing) + "."
             if missing else "")
    return {"items": out, "missing_count": len(missing), "requester_reply": reply,
            "escalation": card.get("escalation", "")}


def l2_diagnose(ticket: dict, card: dict, evidence: dict, complete) -> dict:
    catalogue = {c["id"]: c for c in evidence["checks"]}
    system = ("You are an L2 analyst. Pick which read-only checks to run, using the card's diagnosis steps. "
              'Reply JSON: {"check_ids":["..."]}. Only use ids from the catalogue.')
    user = (_ticket_block(ticket) + "\n\nDiagnosis steps:\n" + "\n".join(card.get("diagnosis") or []) +
            "\n\nCatalogue:\n" + "\n".join(f"{c['id']}: {c['description']}" for c in evidence["checks"]))
    ids = [i for i in (complete(system, user).get("check_ids") or []) if i in catalogue][:8]
    if not ids:
        ids = [c["id"] for c in evidence["checks"]]
    checks = [{"id": i, "what": catalogue[i]["description"], "query": catalogue[i]["query"],
               "found": catalogue[i]["result"], "facts": catalogue[i].get("facts", {})} for i in ids]
    system2 = ("You are an L2 analyst. From the check results, state the root cause and whether it needs an L3 data fix. "
               'Reply JSON: {"conclusion":"...","needs_data_fix":true|false,"confidence":"high|medium|low",'
               '"ok":{"<check id>":true|false}} where ok=false means the check found a problem.')
    user2 = (_ticket_block(ticket) + "\n\nCard cause: " + str(card.get("cause", "")) + "\n\nResults:\n" +
             "\n".join(f"{c['id']}: {c['found']}" for c in checks))
    res = complete(system2, user2)
    ok = res.get("ok") if isinstance(res.get("ok"), dict) else {}
    for c in checks:
        c["ok"] = bool(ok.get(c["id"], True))
    return {"checks": checks, "conclusion": str(res.get("conclusion") or ""),
            "needs_data_fix": bool(res.get("needs_data_fix")), "confidence": str(res.get("confidence") or "medium"),
            "evidence_label": evidence.get("_label", "")}


L3_SYSTEM = (
    "You are an L3 Guidewire engineer. Write a Gosu script that corrects ONE policy's data, and a change requirement "
    "for the permanent fix. Rules for the script: first line is a // comment with the ticket id; start with "
    "'uses gw.transaction.Transaction'; wrap changes in Transaction.runWithNewBundle(\\b -> { ... }); mention only the "
    "given policy number in double quotes; no deletes; at most 5 field assignments, one per line like 'obj.Field = value'. "
    'Reply JSON: {"gosu":"...","explanation":"...","expected_effect":"...","requirement":{"title","problem",'
    '"root_cause","evidence":[],"acceptance_criteria":[],"impacted_modules":[],"test_scenarios":[],"risk"}}')


def l3_author(ticket_id: str, ticket: dict, card: dict, l2: dict, evidence: dict, complete) -> dict:
    policy = evidence["policy_number"]
    base = (f"Ticket id: {ticket_id}\nPolicy number: {policy}\nAudit job: {evidence['audit_job']}\n"
            f"{_ticket_block(ticket)}\nL2 conclusion: {l2['conclusion']}\n"
            "Findings:\n" + "\n".join(f"- {c['what']}: {c['found']}" for c in l2["checks"]) +
            f"\nCard permanent fix: {card.get('permanent_fix', '')}")
    prompt, repairs, res, report = base, 0, {}, {}
    while True:
        res = complete(L3_SYSTEM, prompt)
        report = gosu_guard.check(str(res.get("gosu") or ""), ticket_id, policy)
        if report["passed"] or repairs >= MAX_REPAIRS:
            break
        repairs += 1
        prompt = base + "\n\nYour previous script failed these checks, fix them:\n" + "\n".join(
            f"- {r['rule']}: {r['detail']}" for r in report["rules"] if not r["ok"])
    req = res.get("requirement") or {}
    req.update({"linked_tickets": card.get("related_tickets") or [ticket_id],
                "source_ticket": str(ticket_id), "source_card": card.get("article_id", "")})
    try:
        req = requirement_doc.validate(req)
    except ValueError as exc:
        req = {"error": str(exc)}
    return {"gosu": str(res.get("gosu") or ""), "explanation": str(res.get("explanation") or ""),
            "expected_effect": str(res.get("expected_effect") or ""), "guard": report, "repairs": repairs,
            "requirement": req}
