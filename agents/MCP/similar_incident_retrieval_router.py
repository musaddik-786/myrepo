"""
similar_incident_retrieval_router.py
───────────────────────────────────────
FastAPI routes for the Similar Incident Retrieval MCP.

Tool / Endpoint map:
  find_similar_incidents   POST /api/similar_incident_retrieval/find
"""
import logging

from fastapi import APIRouter, HTTPException

from similar_incident_retrieval_mcp import handler
from similar_incident_retrieval_mcp.models import SimilarIncidentRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/similar_incident_retrieval/find",
    operation_id="find_similar_incidents",
    summary="Find past resolved tickets similar to a given one, over ticket_records",
    tags=["SimilarIncidentRetrieval"],
)
def find_similar_incidents(request: SimilarIncidentRequest):
    try:
        return handler.find_similar_incidents(
            request.id, request.title, request.description,
            request.module, request.severity, request.created,
        )
    except Exception as e:
        log.exception("find_similar_incidents error")
        raise HTTPException(status_code=500, detail=str(e))
