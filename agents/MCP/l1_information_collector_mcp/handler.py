"""
handler.py — L1 Information Collector
────────────────────────────────────────
Thin wrapper around retrieval_agent/fix_steps.py's existing l1_guide() --
checks a matched KB card's info_to_collect checklist against the ticket's
TEXT ONLY (never evidence/diagnosis). Depends on KB Matching for the card
itself -- matched in-process via retrieval_agent.kb_resolver.resolve(),
same as app/routers/fix.py's _match_card() helper.
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import HTTPException

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent import fix_steps  # noqa: E402
from retrieval_agent.kb_resolver import fetch_units, resolve  # noqa: E402
from retrieval_agent.providers import KB_EMBEDDING_DIMENSIONS, Settings, complete_json, embed_texts  # noqa: E402


def _match_card(ticket: dict, settings: Settings) -> dict:
    res = resolve(
        ticket, fetch_units(settings), settings,
        lambda text: embed_texts(settings, [text], KB_EMBEDDING_DIMENSIONS)[0],
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )
    if not res.get("matched") or not res.get("unit"):
        raise HTTPException(409, "No knowledge card matches this ticket, so there is nothing to guide the requester on.")
    return res["unit"]["content"]


def collect_l1_info(title: str | None, description: str | None) -> dict:
    """
    Re-matches the ticket to its KB card, then checks the card's
    info_to_collect checklist against the ticket's text only. Returns
    card (the matched KB card content, so a caller can chain straight into
    L2 without re-matching), l1 (the exact dict to pass straight through to
    save_l1_result's own `l1` argument -- items, missing_count,
    requester_reply, escalation, already separated from `card` -- never
    reconstruct or summarize this field yourself), plus the same
    items/missing_count/requester_reply/escalation at the top level too.

    Raises 409 if no KB card matches -- there is nothing to guide on.
    """
    settings = Settings.load()
    ticket = {"title": title, "description": description}
    card = _match_card(ticket, settings)
    guide = fix_steps.l1_guide(ticket, card, lambda s, u: complete_json(settings, s, u))
    return {"card": card, "l1": guide, **guide}
