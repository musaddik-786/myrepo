"""
knowledge_ingestion_curation_router.py
────────────────────────────────────────
FastAPI routes for the Knowledge Ingestion & Curation MCP.

Tool / Endpoint map:
  run_ingestion          POST /api/knowledge_ingestion_curation/run
  ingest_closed_ticket   POST /api/knowledge_ingestion_curation/ingest_closed_ticket
"""
import logging

from fastapi import APIRouter, HTTPException

from knowledge_ingestion_curation_mcp import handler
from knowledge_ingestion_curation_mcp.models import IngestClosedTicketRequest, IngestionRunRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/knowledge_ingestion_curation/run",
    operation_id="run_ingestion",
    summary="Refresh the Knowledge Store from raw sources (ingest -> structure/embed -> SME curation gate)",
    tags=["KnowledgeIngestionCuration"],
)
def run_ingestion(request: IngestionRunRequest):
    """
    Wraps backend/pipeline.py's run_pipeline(). Omit `sources` to refresh
    all 4 (tickets, chat_rca, release_notes, runbooks). Set `force=true` to
    re-tag/re-embed every selected record even if unchanged since the last run.
    """
    try:
        return handler.run_ingestion(request.sources, request.force)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("run_ingestion error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/knowledge_ingestion_curation/ingest_closed_ticket",
    operation_id="ingest_closed_ticket",
    summary="Persist a closed ticket's resolution and embed it into the live Knowledge Store (ticket_records)",
    tags=["KnowledgeIngestionCuration"],
)
def ingest_closed_ticket(request: IngestClosedTicketRequest):
    """
    For a real, osTicket-synced ticket (ticket_records, not data/raw/tickets.json):
    writes its resolution/resolution_type and embeds title+description+resolution
    so Similar Incident Retrieval can find it. ticket_store=False means no such
    ticket_id exists.
    """
    try:
        return handler.ingest_closed_ticket(request.ticket_id, request.resolution_type, request.notes)
    except Exception as e:
        log.exception("ingest_closed_ticket error")
        raise HTTPException(status_code=500, detail=str(e))
