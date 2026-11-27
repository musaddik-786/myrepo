"""
handler.py — Ticket Classification & Triage
─────────────────────────────────────────────
Wraps the existing per-ticket classification/triage logic (agents/
ticket_classification_triage/service.py) as an MCP tool -- same controlled
taxonomy, same ticket_records persistence, same confidence-based
AutoApproved/PendingReview gate. No new business logic lives here; this is
the exact same code path the osTicket-sync trigger route already uses.
"""
from __future__ import annotations

from agents.ticket_classification_triage.service import classify_and_persist


def classify_ticket_record(record_id: str) -> dict:
    """
    Classifies and triages a ticket_records row by record_id and persists
    the result. Raises LookupError if no such (non-removed) record exists,
    RuntimeError if the classification model call failed, ValueError if
    the agent is misconfigured.
    """
    return classify_and_persist(record_id)
