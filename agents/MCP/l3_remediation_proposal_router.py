"""
l3_remediation_proposal_router.py
─────────────────────────────────────
FastAPI routes for the L3 Remediation Proposal MCP.

Tool / Endpoint map:
  author_remediation       POST /api/l3_remediation_proposal/author
  requirement_to_markdown  POST /api/l3_remediation_proposal/requirement/markdown
"""
import logging

from fastapi import APIRouter, HTTPException

from l3_remediation_proposal_mcp import handler
from l3_remediation_proposal_mcp.models import L3AuthorRequest, RequirementMarkdownRequest

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/l3_remediation_proposal/author",
    operation_id="author_remediation",
    summary="Draft a Gosu remediation script and change-requirement document (requires L2 needs_data_fix=true)",
    tags=["L3RemediationProposal"],
)
def author_remediation(request: L3AuthorRequest):
    try:
        return handler.author_remediation(
            request.ticket_id, request.title, request.description,
            request.card, request.l2, request.evidence,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("author_remediation error")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/api/l3_remediation_proposal/requirement/markdown",
    operation_id="requirement_to_markdown",
    summary="Render an L3 change-requirement document to Markdown",
    tags=["L3RemediationProposal"],
)
def requirement_to_markdown(request: RequirementMarkdownRequest):
    try:
        return handler.requirement_to_markdown(request.requirement)
    except Exception as e:
        log.exception("requirement_to_markdown error")
        raise HTTPException(status_code=500, detail=str(e))
