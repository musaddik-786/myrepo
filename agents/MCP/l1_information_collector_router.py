"""
l1_information_collector_router.py
──────────────────────────────────────
FastAPI routes for the L1 Information Collector MCP.

Tool / Endpoint map:
  collect_l1_info   POST /api/l1_information_collector/collect
"""
import logging

from fastapi import APIRouter, HTTPException

from l1_information_collector_mcp import handler
from l1_information_collector_mcp.models import L1CollectRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/l1_information_collector/collect",
    operation_id="collect_l1_info",
    summary="Check a matched KB card's info_to_collect checklist against the ticket's text",
    tags=["L1InformationCollector"],
)
def collect_l1_info(request: L1CollectRequest):
    try:
        return handler.collect_l1_info(request.title, request.description)
    except HTTPException:
        raise
    except Exception as e:
        log.exception("collect_l1_info error")
        raise HTTPException(status_code=500, detail=str(e))
