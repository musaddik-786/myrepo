"""
orchestrator_router.py
───────────────────────────
FastAPI routes for the Orchestrator Agent's own state/persistence MCP
tools -- not a ticket-domain agent. These are what let the LLM-driven
Orchestrator Agent (agents/orchestrator/server.py) actually persist each
stage's result to fix_runs, and read back a ticket's current state before
continuing to a later stage.

Tool / Endpoint map:
  get_ticket_run    GET  /api/orchestrator_state/{ticket_id}
  save_l1_result    POST /api/orchestrator_state/{ticket_id}/l1
  save_l2_result    POST /api/orchestrator_state/{ticket_id}/l2
  save_l3_result    POST /api/orchestrator_state/{ticket_id}/l3
"""
import logging

from fastapi import APIRouter, HTTPException

from orchestrator_mcp import handler
from orchestrator_mcp.models import SaveL1ResultRequest, SaveL2ResultRequest, SaveL3ResultRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/orchestrator_state/{ticket_id}",
    operation_id="get_ticket_run",
    summary="Get a ticket's current orchestrator run state (stage, status, outputs)",
    tags=["OrchestratorState"],
)
def get_ticket_run(ticket_id: str):
    return handler.get_ticket_run(ticket_id)


@router.post(
    "/api/orchestrator_state/{ticket_id}/l1",
    operation_id="save_l1_result",
    summary="Persist the L1 stage's result (KB card, L1 checklist, evidence, similar incidents)",
    tags=["OrchestratorState"],
)
def save_l1_result(ticket_id: str, request: SaveL1ResultRequest):
    try:
        return handler.save_l1_result(ticket_id, request.card, request.l1, request.evidence, request.similar, request.user)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/api/orchestrator_state/{ticket_id}/l2",
    operation_id="save_l2_result",
    summary="Persist the L2 Diagnostic Agent's result",
    tags=["OrchestratorState"],
)
def save_l2_result(ticket_id: str, request: SaveL2ResultRequest):
    try:
        return handler.save_l2_result(ticket_id, request.l2, request.user)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post(
    "/api/orchestrator_state/{ticket_id}/l3",
    operation_id="save_l3_result",
    summary="Persist the L3 Remediation Proposal Agent's result",
    tags=["OrchestratorState"],
)
def save_l3_result(ticket_id: str, request: SaveL3ResultRequest):
    try:
        return handler.save_l3_result(ticket_id, request.l3, request.run_by, request.user)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
