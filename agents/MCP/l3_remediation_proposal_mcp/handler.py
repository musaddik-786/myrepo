"""
handler.py — L3 Remediation Proposal
────────────────────────────────────────
Thin wrapper around retrieval_agent/fix_steps.py's existing l3_author() --
drafts a Gosu script + change-requirement document, enforced by
gosu_guard.py's deterministic safety rules with one automatic self-repair
retry. Only runs when L2 found needs_data_fix=true; otherwise there is
nothing to remediate.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent import fix_steps, requirement_doc  # noqa: E402
from retrieval_agent.providers import Settings, complete_json  # noqa: E402


def author_remediation(
    ticket_id: str, title: str | None, description: str | None,
    card: dict[str, Any], l2: dict[str, Any], evidence: dict[str, Any],
) -> dict:
    """
    Drafts a Gosu remediation script and a change-requirement document.
    Returns gosu, explanation, expected_effect, guard (gosu_guard.check()'s
    report: passed + rules), repairs (0 or 1 automatic self-repair retries),
    requirement.

    Raises if L2's `l2.needs_data_fix` is not true -- there is nothing to
    remediate.
    """
    if not l2.get("needs_data_fix"):
        raise ValueError("L2 found no data fix is needed; nothing for L3 to remediate.")

    settings = Settings.load()
    ticket = {"title": title, "description": description}
    return fix_steps.l3_author(
        ticket_id, ticket, card, l2, evidence,
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )


def requirement_to_markdown(requirement: dict) -> dict:
    """Renders an L3 change-requirement document to Markdown."""
    return {"markdown": requirement_doc.to_markdown(requirement)}
