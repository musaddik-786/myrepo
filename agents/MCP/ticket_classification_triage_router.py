"""
ticket_classification_triage_router.py
───────────────────────────────────────────
FastAPI routes for the Ticket Classification & Triage MCP.

Tool / Endpoint map:
  classify_ticket_record   POST /api/ticket_classification_triage/classify
"""
import logging

from fastapi import APIRouter, HTTPException

from ticket_classification_triage_mcp import handler
from ticket_classification_triage_mcp.models import ClassifyTicketRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/ticket_classification_triage/classify",
    operation_id="classify_ticket_record",
    summary="Classify and triage a ticket_records row by record_id and persist the result",
    tags=["TicketClassificationTriage"],
)
def classify_ticket_record(request: ClassifyTicketRequest):
    try:
        return handler.classify_ticket_record(request.record_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.exception("classify_ticket_record error")
        raise HTTPException(status_code=500, detail=str(e))
