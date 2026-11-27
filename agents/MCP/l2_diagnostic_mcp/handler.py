"""
handler.py — L2 Diagnostic
──────────────────────────────
Thin wrapper around retrieval_agent/fix_steps.py's existing l2_diagnose() --
applies the KB card's diagnosis steps to the fetched evidence and reaches a
needs_data_fix verdict (the real gate for L3). Depends on the KB card (L1)
and the evidence already having been produced -- this does not re-match
the card or re-fetch evidence itself.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent import fix_steps  # noqa: E402
from retrieval_agent.providers import Settings, complete_json  # noqa: E402


def diagnose(title: str | None, description: str | None, card: dict[str, Any], evidence: dict[str, Any]) -> dict:
    """
    Applies the KB card's diagnosis steps to the fetched evidence. Returns
    checks, conclusion, needs_data_fix (the gate for whether L3 should run),
    confidence, evidence_label.
    """
    settings = Settings.load()
    ticket = {"title": title, "description": description}
    return fix_steps.l2_diagnose(
        ticket, card, evidence,
        lambda system_prompt, user_prompt: complete_json(settings, system_prompt, user_prompt),
    )
