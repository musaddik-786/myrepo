"""
kb_matching_router.py
────────────────────────
FastAPI routes for the KB Matching MCP.

Tool / Endpoint map:
  list_kb_units   GET  /api/kb_matching/units
  match_kb_card   POST /api/kb_matching/match
"""
import logging

from fastapi import APIRouter, HTTPException

from kb_matching_mcp import handler
from kb_matching_mcp.models import KbMatchRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/kb_matching/units",
    operation_id="list_kb_units",
    summary="List the SME-authored Resolution Unit (knowledge base) cards",
    tags=["KbMatching"],
)
def list_kb_units():
    try:
        return handler.list_kb_units()
    except Exception as e:
        log.exception("list_kb_units error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/kb_matching/match",
    operation_id="match_kb_card",
    summary="Match a ticket's title/description against the knowledge base cards",
    tags=["KbMatching"],
)
def match_kb_card(request: KbMatchRequest):
    """
    Returns matched=false with candidates (ranked near-misses) when nothing
    in the knowledge base resembles the ticket, or when the LLM explicitly
    rejects every candidate -- this is a normal result, not an error.
    """
    try:
        return handler.match_kb_card(request.title, request.description)
    except Exception as e:
        log.exception("match_kb_card error")
        raise HTTPException(status_code=500, detail=str(e))
