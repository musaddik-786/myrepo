"""
handler.py — Human Approval
───────────────────────────────
Pure deterministic logic -- no LLM, no DB. Enforces: cannot approve your
own work, cannot approve a script that failed its safety guard, and an
approval needs a change-control id. Nothing here ever runs the script; it
only approves or rejects it.
"""
from __future__ import annotations

import hashlib


def decide_approval(
    approve: bool, gosu: str, guard_passed: bool, run_by: str,
    approver: str, change_id: str = "", note: str = "",
) -> dict:
    """
    Approves or rejects an L3-proposed Gosu script. Raises 403 if the
    approver is the same person who ran L3; raises 422 if the script
    failed its safety guard or no change_id is given when approving.
    Returns status, approver, change_id, note, and script_sha256 (a
    tamper-proof fingerprint of the exact script text that was decided on).
    """
    if not approver.strip():
        raise ValueError("Approver is required.")
    if approve:
        if approver.strip().lower() == run_by.strip().lower():
            raise PermissionError("The approver cannot be the person who ran L3.")
        if not guard_passed:
            raise ValueError("The script failed the safety checks and cannot be approved.")
        if not change_id.strip():
            raise ValueError("A change-control id is required to approve.")
    return {
        "status": "approved" if approve else "rejected",
        "approver": approver,
        "change_id": change_id,
        "note": note,
        "script_sha256": hashlib.sha256(gosu.encode()).hexdigest(),
    }
