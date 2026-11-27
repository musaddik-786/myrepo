"""
human_approval_router.py
────────────────────────────
FastAPI routes for the Human Approval MCP.

Tool / Endpoint map:
  decide_approval   POST /api/human_approval/decide
"""
import logging

from fastapi import APIRouter, HTTPException

from human_approval_mcp import handler
from human_approval_mcp.models import ApprovalDecisionRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/human_approval/decide",
    operation_id="decide_approval",
    summary="Approve or reject an L3-proposed Gosu script (never runs it)",
    tags=["HumanApproval"],
)
def decide_approval(request: ApprovalDecisionRequest):
    try:
        return handler.decide_approval(
            request.approve, request.gosu, request.guard_passed,
            request.run_by, request.approver, request.change_id, request.note,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("decide_approval error")
        raise HTTPException(status_code=500, detail=str(e))
