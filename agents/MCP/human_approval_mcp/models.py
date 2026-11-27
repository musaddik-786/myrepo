from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approve: bool  # True = approve, False = reject
    gosu: str  # the L3-proposed Gosu script text
    guard_passed: bool  # from l3_remediation_proposal_mcp's guard.passed
    run_by: str  # who ran L3 -- cannot also be the approver
    approver: str
    change_id: str = ""
    note: str = ""
