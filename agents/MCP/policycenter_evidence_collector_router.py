"""
policycenter_evidence_collector_router.py
─────────────────────────────────────────────
FastAPI routes for the PolicyCenter Evidence Planner/Collector MCP.

Tool / Endpoint map:
  collect_evidence   POST /api/policycenter_evidence_collector/collect
"""
import logging

from fastapi import APIRouter, HTTPException

from policycenter_evidence_collector_mcp import handler
from policycenter_evidence_collector_mcp.models import EvidenceRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/policycenter_evidence_collector/collect",
    operation_id="collect_evidence",
    summary="Load the static demo PolicyCenter evidence fixture for a KB card's unit_id",
    tags=["PolicyCenterEvidenceCollector"],
)
def collect_evidence(request: EvidenceRequest):
    try:
        return handler.collect_evidence(request.unit_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.exception("collect_evidence error")
        raise HTTPException(status_code=500, detail=str(e))
