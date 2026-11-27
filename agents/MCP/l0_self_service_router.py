"""
l0_self_service_router.py
─────────────────────────────
FastAPI routes for the L0 Self-Service MCP.

Tool / Endpoint map:
  run_l0_chat       POST /api/l0_self_service/chat
  record_outcome    POST /api/l0_self_service/outcome
  get_stats         GET  /api/l0_self_service/stats
"""
import logging

from fastapi import APIRouter, HTTPException

from l0_self_service_mcp import handler
from l0_self_service_mcp.models import L0ChatRequest, L0OutcomeRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/l0_self_service/chat",
    operation_id="run_l0_chat",
    summary="Answer a requester's chat turn from a matched KB card's self-service steps only",
    tags=["L0SelfService"],
)
def run_l0_chat(request: L0ChatRequest):
    try:
        return handler.run_l0_chat([m.model_dump() for m in request.messages], request.session_id)
    except Exception as e:
        log.exception("run_l0_chat error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/l0_self_service/outcome",
    operation_id="record_outcome",
    summary="Record how an L0 chat session ended (open / resolved / ticket_created)",
    tags=["L0SelfService"],
)
def record_outcome(request: L0OutcomeRequest):
    try:
        return handler.record_outcome(request.session_id, request.outcome)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("record_outcome error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/l0_self_service/stats",
    operation_id="get_stats",
    summary="Get L0 deflection-rate stats (chats, resolved_without_ticket, tickets_created, deflection_rate)",
    tags=["L0SelfService"],
)
def get_stats():
    try:
        return handler.get_stats()
    except Exception as e:
        log.exception("get_stats error")
        raise HTTPException(status_code=500, detail=str(e))
