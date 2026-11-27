"""
handler.py — KB Matching
──────────────────────────
Thin wrapper around retrieval_agent/kb_resolver.py's existing resolve()
function -- matches a ticket against the 13 SME-authored Resolution Unit
cards (knowledge/units/*.json), the same logic already powering
app/routers/kb.py's /api/kb/resolve. No ranking/matching logic lives here.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent.kb_resolver import fetch_units, resolve  # noqa: E402
from retrieval_agent.providers import KB_EMBEDDING_DIMENSIONS, Settings, complete_json, embed_texts  # noqa: E402


def list_kb_units() -> list[dict]:
    """
    Lists the SME-authored Resolution Unit cards (unit_id, title, module,
    category, keywords) currently in the knowledge/units/ store, without
    running any matching.
    """
    settings = Settings.load()
    units = fetch_units(settings)
    out = []
    for u in units:
        content = u.get("content") or {}
        out.append({
            "unit_id": content.get("unit_id") or u.get("id"),
            "title": content.get("title"),
            "module": content.get("module"),
            "category": content.get("category"),
            "keywords": content.get("keywords"),
        })
    return out


def match_kb_card(title: str | None, description: str | None) -> dict:
    """
    Matches a ticket's title/description against the knowledge base cards.
    Returns matched (bool), unit (the full matched card wrapper -- unit_id,
    article_id, version, kb_version, review_status, content -- or null),
    card (the exact dict to pass straight through to save_l1_result's own
    `card` argument and to collect_evidence/diagnose/author_remediation's
    own `card` argument when matched -- i.e. unit["content"], which already
    carries its own article_id/unit_id/title/play; null when not matched --
    never reconstruct or summarize this field yourself), confidence,
    reason, missing_info, candidates (ranked near-misses even when there is
    no match), and verified.
    """
    settings = Settings.load()
    ticket = {"title": title, "description": description}
    units = fetch_units(settings)
    result = resolve(
        ticket,
        units,
        settings,
        lambda text: embed_texts(settings, [text], KB_EMBEDDING_DIMENSIONS)[0],
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )
    result["card"] = result["unit"]["content"] if result.get("matched") and result.get("unit") else None
    return result
