import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from retrieval_agent import fix_steps, gosu_guard, requirement_doc  # noqa: E402

GOOD = ('// Ticket 946493: fix\nuses gw.transaction.Transaction\n'
        'Transaction.runWithNewBundle(\\b -> {\n  var e = b.add(x("PC-0078231"))\n  e.AuditedBasis = 440000\n})')
REQ = {"title": "t", "problem": "p", "root_cause": "r", "evidence": ["e"], "acceptance_criteria": ["a"],
       "impacted_modules": ["m"], "test_scenarios": ["s"], "risk": "low"}
CARD = {"unit_id": "PC-AUD-01", "article_id": "KB-PC-AUD-001", "related_tickets": ["T0060"],
        "diagnosis": ["step"], "cause": "c", "permanent_fix": "pf", "info_to_collect": ["a", "b"], "escalation": "e"}


def _rules(report):
    return {r["rule"]: r["ok"] for r in report["rules"]}


def test_guard_accepts_good_script():
    assert gosu_guard.check(GOOD, "946493", "PC-0078231")["passed"]


def test_guard_rejects_delete_second_policy_no_transaction():
    bad_delete = GOOD.replace("e.AuditedBasis = 440000", "b.remove(e)")
    assert not gosu_guard.check(bad_delete, "946493", "PC-0078231")["passed"]
    two = GOOD.replace('"PC-0078231"', '"PC-0078231", "PC-0099999"')
    assert not _rules(gosu_guard.check(two, "946493", "PC-0078231"))["Touches only the ticket's policy"]
    no_tx = GOOD.replace("Transaction.runWithNewBundle", "foo")
    assert not _rules(gosu_guard.check(no_tx, "946493", "PC-0078231"))["Runs inside one bundle transaction"]
    assert not _rules(gosu_guard.check(GOOD.replace("946493", "1"), "946493", "PC-0078231"))["Header comment names the ticket"]


def test_requirement_validates_and_renders():
    doc = {**REQ, "linked_tickets": ["T1"], "source_ticket": "1", "source_card": "KB"}
    assert "## Acceptance criteria" in requirement_doc.to_markdown(doc)
    try:
        requirement_doc.validate({"title": "x"})
        assert False
    except ValueError as exc:
        assert "problem" in str(exc)


def test_l3_repairs_after_guard_failure():
    calls = []
    def complete(system, user):
        calls.append(user)
        script = GOOD.replace("runWithNewBundle", "foo") if len(calls) == 1 else GOOD
        return {"gosu": script, "explanation": "x", "expected_effect": "y", "requirement": dict(REQ)}
    ev = fix_steps.load_evidence("PC-AUD-01")
    l2 = {"conclusion": "c", "checks": [{"what": "w", "found": "f"}]}
    out = fix_steps.l3_author("946493", {"title": "t"}, CARD, l2, ev, complete)
    assert out["repairs"] == 1 and out["guard"]["passed"] and "failed these checks" in calls[1]
    assert out["requirement"]["source_card"] == "KB-PC-AUD-001"


def test_l2_uses_only_catalogue_ids():
    ev = fix_steps.load_evidence("PC-AUD-01")
    def complete(system, user):
        if "Pick which" in system:
            return {"check_ids": ["exposure_basis", "made_up"]}
        return {"conclusion": "c", "needs_data_fix": True, "confidence": "high", "ok": {"exposure_basis": False}}
    out = fix_steps.l2_diagnose({"title": "t"}, CARD, ev, complete)
    assert [c["id"] for c in out["checks"]] == ["exposure_basis"] and out["checks"][0]["ok"] is False


def test_l1_flags_missing_items():
    out = fix_steps.l1_guide({"title": "t"}, CARD, lambda s, u: {"items": [{"index": 0, "answered": True, "found": "q"}]})
    assert out["missing_count"] == 1 and "b" in out["requester_reply"]


def test_router_approval_rules(monkeypatch):
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from app.routers import fix
    monkeypatch.delenv("PG_HOST", raising=False)
    fix._MEM.clear()
    app = FastAPI(); app.include_router(fix.router); c = TestClient(app)
    fix._MEM["9"] = {"ticket_id": "9", "stage": "l3", "status": "open", "run_by": "sai",
                     "outputs": {"l3": {"gosu": GOOD, "guard": {"passed": True, "rules": []}, "requirement": {}}}}
    assert c.post("/api/fix/9/approve", json={"approver": "sai", "change_id": "CHG1"}).status_code == 403
    assert c.post("/api/fix/9/approve", json={"approver": "meera"}).status_code == 422
    r = c.post("/api/fix/9/approve", json={"approver": "meera", "change_id": "CHG1"})
    assert r.status_code == 200 and r.json()["outputs"]["decision"]["script_sha256"]
    assert c.post("/api/fix/9/reject", json={"approver": "meera"}).status_code == 409


def test_l0_shows_only_self_service_block():
    from types import SimpleNamespace
    import kb_load
    from retrieval_agent import l0_chat
    sys.path.insert(0, str(ROOT / "scripts"))
    units = [{"unit_id": u["unit_id"], "article_id": u["article_id"], "title": u["title"],
              "match_text": kb_load.match_text(u), "version": u["version"], "review_status": "x",
              "kb_version": "k", "content": u, "embedding": [1.0, 0.0]} for u in kb_load.load_units()]
    settings = SimpleNamespace(rrf_constant=60)
    def complete(s, u):
        return {"unit_id": "PC-AUD-01", "confidence": "high", "reason": "r", "missing_info": []}
    msgs = [{"role": "user", "content": "Audit premium decreased although payroll increased"}]
    out = l0_chat.chat(msgs, units, settings, lambda t: [1.0, 0.0], complete)
    assert out["steps"] and out["matched_card"] == "KB-PC-AUD-001"
    blob = json.dumps(out)
    assert "Hold the audit invoice in Billing" not in blob and "RB-AUD" not in blob   # L2/L3 content stays internal
    assert l0_chat.self_service_of("PC-AUD-02") is None   # cards without a reviewed block never answer


def test_l0_outcomes_and_stats(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import l0
    monkeypatch.setenv("FIX_STORE", "memory")
    l0._MEM.clear()
    app = FastAPI(); app.include_router(l0.router); c = TestClient(app)
    c.post("/api/l0/outcome", json={"session_id": "a", "outcome": "resolved"})
    c.post("/api/l0/outcome", json={"session_id": "b", "outcome": "ticket_created"})
    c.post("/api/l0/outcome", json={"session_id": "b", "outcome": "resolved"})   # a ticket stays a ticket
    assert c.post("/api/l0/outcome", json={"session_id": "c", "outcome": "bogus"}).status_code == 422
    s = c.get("/api/l0/stats").json()
    assert s == {"chats": 2, "resolved_without_ticket": 1, "tickets_created": 1, "deflection_rate": 50}


def test_l0_ticket_calls_osticket(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import l0
    monkeypatch.setenv("FIX_STORE", "memory")
    l0._MEM.clear()
    monkeypatch.setattr(l0, "create_ticket", lambda *a: "123456")
    app = FastAPI(); app.include_router(l0.router); c = TestClient(app)
    body = {"session_id": "s", "name": "A", "email": "a@b.co", "title": "t", "description": "d", "module": "PolicyCenter"}
    assert c.post("/api/l0/ticket", json=body).json() == {"ticket_number": "123456"}
    assert l0._MEM["s"]["outcome"] == "ticket_created" and l0._MEM["s"]["ticket_ref"] == "123456"
    assert c.post("/api/l0/ticket", json={**body, "name": " "}).status_code == 422


def _resolve_client(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import fix
    monkeypatch.delenv("PG_HOST", raising=False)
    fix._MEM.clear(); fix._MEM_AUDIT.clear()
    app = FastAPI(); app.include_router(fix.router)
    return fix, TestClient(app)


def test_resolve_rules_and_close(monkeypatch):
    fix, c = _resolve_client(monkeypatch)
    body = {"level": "l2", "resolution_type": "Workaround", "notes": "Basis corrected", "resolved_by": "sai"}
    assert c.post("/api/fix/7/resolve", json=body).status_code == 409           # L2 not run
    fix._MEM["7"] = {"ticket_id": "7", "stage": "l3", "status": "open", "run_by": "sai",
                     "outputs": {"l1": {}, "l2": {"conclusion": "x"}, "l3": {"gosu": GOOD}}}
    assert c.post("/api/fix/7/resolve", json={**body, "level": "l3"}).status_code == 409   # L3 not approved
    assert c.post("/api/fix/7/resolve", json={**body, "resolution_type": "Nope"}).status_code == 422
    assert c.post("/api/fix/7/resolve", json={**body, "notes": "  "}).status_code == 422
    r = c.post("/api/fix/7/resolve", json=body)
    assert r.status_code == 200 and r.json()["status"] == "closed"
    assert r.json()["outputs"]["resolution"]["embedded"] is False               # no store configured
    assert c.post("/api/fix/7/resolve", json=body).status_code == 409           # already closed
    assert c.post("/api/fix/7/run/l2", json={}).status_code == 409              # closed tickets stay closed
    assert c.post("/api/fix/7/approve", json={"approver": "m", "change_id": "C"}).status_code == 409
    assert fix._MEM_AUDIT[-1]["action"] == "closed"


def test_resolve_writes_and_embeds(monkeypatch):
    fix, c = _resolve_client(monkeypatch)
    calls = []

    class Cur:
        def __init__(self, row=None): self.row = row
        def fetchone(self): return self.row

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=()):
            calls.append((sql.split()[0], params))
            return Cur({"record_id": "osticket-1", "title": "T", "raw_text": "R"}) if "RETURNING" in sql else Cur()

    monkeypatch.setattr(fix, "_use_pg", lambda: True)
    monkeypatch.setattr(fix, "_pg", lambda: Conn())
    monkeypatch.setattr(fix, "save_run", lambda run: fix._MEM.__setitem__(run["ticket_id"], run))
    monkeypatch.setattr(fix, "audit", lambda *a: None)
    monkeypatch.setattr(fix, "load_run", lambda t: fix._MEM.get(t, {"ticket_id": t, "stage": "l1", "status": "open", "outputs": {"l1": {}}, "run_by": None}))
    monkeypatch.setattr(fix.Settings, "load", classmethod(lambda cls: None))
    import retrieval_agent.providers as prov
    monkeypatch.setattr(fix, "embed_texts", lambda s, t: [[0.5] * prov.EMBEDDING_DIMENSIONS])
    body = {"level": "l1", "resolution_type": "UserErrorClosed", "notes": "Fixed", "resolved_by": "sai"}
    r = c.post("/api/fix/1/resolve", json=body).json()["outputs"]["resolution"]
    assert r["ticket_store"] and r["embedded"]
    assert [k for k, _ in calls] == ["UPDATE", "UPDATE"] and calls[0][1][:3] == ("Fixed", "UserErrorClosed", "1")
    fix._MEM.clear()
    def boom(s, t): raise RuntimeError("down")
    monkeypatch.setattr(fix, "embed_texts", boom)
    r = c.post("/api/fix/1/resolve", json=body).json()["outputs"]["resolution"]
    assert r["ticket_store"] and r["embedded"] is False                         # still saved
