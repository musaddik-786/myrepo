"""Ticket Classification & Triage Agent endpoint for ticket_records rows.

This is what clears the 'NeedsRetag' status every osTicket-synced ticket starts
with (see app/services/osticket.py) -- it never touches the sync itself, only
the tagging fields the sync deliberately leaves as placeholders.

The fetch+classify+persist logic itself lives in service.classify_and_persist,
shared with the ticket_classification_triage MCP tool (agents/MCP/
ticket_classification_triage_mcp/handler.py) so the sync-trigger route below
and the MCP tool run the exact same code path.
"""
from fastapi import APIRouter, HTTPException

from agents.ticket_classification_triage.service import classify_and_persist

router = APIRouter(prefix="/api/classify")


@router.post("/{record_id}")
def classify(record_id: str) -> dict:
    try:
        return classify_and_persist(record_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(503, f"Agent configuration error: {exc}") from exc
