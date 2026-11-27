"""Deterministic safety checks for a generated Gosu script. Plain code, never an LLM."""
import re

ALLOWED_USES = {"gw.transaction.Transaction", "gw.api.database.Query", "gw.api.util.DateUtil"}
FORBIDDEN = re.compile(
    r"\.remove\(|\bdelete\b|\.Bundle\.remove|System\.exit|\bRuntime\b|\bjava\.io\b|\bjava\.net\b|"
    r"\bProcessBuilder\b|\bexecuteUpdate\b|\bdrop\s+table\b|\.commit\(\)\s*;?\s*\.commit", re.I)
MAX_FIELD_UPDATES = 5


def check(script: str, ticket_id: str, policy_number: str) -> dict:
    """Return {passed, rules:[{rule, ok, detail}]}. All rules must pass."""
    text = script or ""
    head = "\n".join(text.splitlines()[:5])
    uses = set(re.findall(r"^\s*uses\s+([\w.]+)", text, re.M))
    policies = set(re.findall(r'"(PC-\d{4,})"', text))
    updates = len(re.findall(r"^\s*\w+\.\w+\s*=[^=]", text, re.M))
    rules = [
        ("Header comment names the ticket", bool(re.search(r"^\s*//.*" + re.escape(str(ticket_id)), head, re.M)),
         f"first lines must contain a // comment with {ticket_id}"),
        ("Runs inside one bundle transaction", "Transaction.runWithNewBundle" in text,
         "use Transaction.runWithNewBundle"),
        ("Touches only the ticket's policy", policies == {policy_number} if policy_number else False,
         f"found policy numbers {sorted(policies)}, expected only {policy_number}"),
        ("No deletes or unsafe calls", not FORBIDDEN.search(text), "remove/delete/IO/network calls are not allowed"),
        ("Only approved libraries", uses <= ALLOWED_USES, f"unapproved: {sorted(uses - ALLOWED_USES)}"),
        (f"At most {MAX_FIELD_UPDATES} field updates", 0 < updates <= MAX_FIELD_UPDATES,
         f"found {updates} field updates"),
    ]
    out = [{"rule": r, "ok": bool(ok), "detail": "" if ok else d} for r, ok, d in rules]
    return {"passed": all(x["ok"] for x in out), "rules": out}
