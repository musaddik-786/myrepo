"""
handler.py — PolicyCenter Evidence Planner/Collector
───────────────────────────────────────────────────────
Thin wrapper around retrieval_agent/fix_steps.py's existing load_evidence().
Status in this codebase is "partially implemented": it only ever reads from
one static demo fixture per unit_id (knowledge/demo/<unit_id>_evidence.json)
-- there is no live PolicyCenter connector yet. This wraps that fixture read
exactly as it exists today.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from retrieval_agent import fix_steps  # noqa: E402


def collect_evidence(unit_id: str) -> dict:
    """
    Loads the static demo evidence fixture for the given KB card unit_id.
    Returns policy_number, audit_job, checks. Raises if no fixture exists
    for this unit_id in this demo (no live PolicyCenter connector yet).
    """
    evidence = fix_steps.load_evidence(unit_id)
    if evidence is None:
        raise ValueError(f"No sample evidence is available for {unit_id} in this demo.")
    return evidence
