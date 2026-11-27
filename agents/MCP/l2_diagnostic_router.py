"""
l2_diagnostic_router.py
───────────────────────────
FastAPI routes for the L2 Diagnostic MCP.

Tool / Endpoint map:
  diagnose   POST /api/l2_diagnostic/diagnose
"""
import logging

from fastapi import APIRouter, HTTPException

from l2_diagnostic_mcp import handler
from l2_diagnostic_mcp.models import L2DiagnoseRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/l2_diagnostic/diagnose",
    operation_id="diagnose",
    summary="Apply a matched KB card's diagnosis steps to collected evidence, reach a needs_data_fix verdict",
    tags=["L2Diagnostic"],
)
def diagnose(request: L2DiagnoseRequest):
    try:
        return handler.diagnose(request.title, request.description, request.card, request.evidence)
    except Exception as e:
        log.exception("diagnose error")
        raise HTTPException(status_code=500, detail=str(e))
