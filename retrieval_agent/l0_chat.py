"""L0 self-service chat: answers a Guidewire user from the card's reviewed self-service text only, or offers a ticket."""
import json
from pathlib import Path

from retrieval_agent.kb_resolver import resolve

UNITS_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "units"


def self_service_of(unit_id: str) -> dict | None:
    """Only the `self_service` block of a card is ever shown to a user; diagnosis, workaround and L3 steps are not."""
    f = UNITS_DIR / f"{unit_id}.json"
    if not f.is_file():
        return None
    block = json.loads(f.read_text()).get("self_service")
    return block if isinstance(block, dict) and block.get("message") and block.get("steps") else None


def module_of(unit_id: str) -> str | None:
    f = UNITS_DIR / f"{unit_id}.json"
    return json.loads(f.read_text()).get("module") if f.is_file() else None


def chat(messages: list[dict], units, settings, embed, complete) -> dict:
    user_text = "\n".join(m["content"] for m in messages if m.get("role") == "user" and m.get("content"))
    if not user_text.strip():
        raise ValueError("Say what is going wrong")
    res = resolve({"title": user_text.splitlines()[0][:120], "description": user_text}, units, settings, embed, complete)
    draft = {"title": user_text.splitlines()[0][:120], "description": user_text}
    base = {"module": None, "matched_card": None, "steps": [], "ask_for": [], "ticket_draft": draft, "verified": res.get("verified", True)}
    unit = res.get("unit")
    ss = self_service_of(unit["unit_id"]) if res.get("matched") and unit and res.get("verified", True) else None
    if not ss:
        return {**base, "resolved_by_bot": False,
                "reply": "I can't resolve this on my own. I've drafted a ticket for the support team with what you told me."}
    return {**base, "resolved_by_bot": False, "module": module_of(unit["unit_id"]), "unit_id": unit["unit_id"],
            "matched_card": unit["article_id"], "steps": ss["steps"],
            "ask_for": res.get("missing_info") or [], "reply": ss["message"]}
