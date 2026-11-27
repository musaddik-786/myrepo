"""
main.py
───────
MCP server entry point for the 9 backend agents built from the Ticket
Classification platform's recommended_agents_roadmap.xlsx. Hosts 9 tool-
domain sub-apps on a single FastAPI app (port 7900), backed by this
project's existing Postgres database and retrieval_agent/backend modules --
no new business logic lives here, only the MCP tool exposure.

Registered sub-apps (all FULL -- wrap already-working code in this repo):
  /api/v1/knowledge_ingestion_curation  — backend/pipeline.py's batch refresh
  /api/v1/kb_matching                    — retrieval_agent/kb_resolver.py
  /api/v1/similar_incident_retrieval      — retrieval_agent/pipeline.py
  /api/v1/l0_self_service                  — retrieval_agent/l0_chat.py
  /api/v1/l1_information_collector          — retrieval_agent/fix_steps.py (l1_guide)
  /api/v1/policycenter_evidence_collector    — retrieval_agent/fix_steps.py (load_evidence)
  /api/v1/l2_diagnostic                       — retrieval_agent/fix_steps.py (l2_diagnose)
  /api/v1/l3_remediation_proposal              — retrieval_agent/fix_steps.py (l3_author)
  /api/v1/human_approval                        — deterministic HITL approval gate
  /api/v1/ticket_classification_triage            — agents/ticket_classification_triage/service.py
  /api/v1/orchestrator_state                        — Orchestrator Agent's own state/persistence tools

Run:
    py -3 agents/MCP/main.py
"""

import os
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent          # agents/MCP
_ROOT = _THIS_DIR.parents[1]                          # repo root
for _p in (str(_ROOT), str(_ROOT / "backend"), str(_THIS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_mcp import FastApiMCP

from knowledge_ingestion_curation_router import router as knowledge_ingestion_curation_router
from kb_matching_router import router as kb_matching_router
from similar_incident_retrieval_router import router as similar_incident_retrieval_router
from l0_self_service_router import router as l0_self_service_router
from l1_information_collector_router import router as l1_information_collector_router
from policycenter_evidence_collector_router import router as policycenter_evidence_collector_router
from l2_diagnostic_router import router as l2_diagnostic_router
from l3_remediation_proposal_router import router as l3_remediation_proposal_router
from human_approval_router import router as human_approval_router
from ticket_classification_triage_router import router as ticket_classification_triage_router
from orchestrator_router import router as orchestrator_state_router

import uvicorn

app = FastAPI(docs_url="/docs", title="Ticket Platform Backend Agents MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _make_cors_app(title: str, description: str = "") -> FastAPI:
    sub = FastAPI(title=title, description=description)
    sub.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return sub


# ── Sub-app: knowledge_ingestion_curation ──────────────────────────────────

knowledge_ingestion_curation_app = _make_cors_app(
    title="knowledge_ingestion_curation_agent_mcps",
    description="MCP tools for refreshing the Knowledge Store from raw sources.",
)
knowledge_ingestion_curation_app.include_router(knowledge_ingestion_curation_router)
FastApiMCP(
    knowledge_ingestion_curation_app,
    include_operations=["run_ingestion", "ingest_closed_ticket"],
).mount_http()
app.mount("/api/v1/knowledge_ingestion_curation", knowledge_ingestion_curation_app)


# ── Sub-app: kb_matching ────────────────────────────────────────────────────

kb_matching_app = _make_cors_app(
    title="kb_matching_agent_mcps",
    description="MCP tools for matching a ticket against the SME-authored knowledge base cards.",
)
kb_matching_app.include_router(kb_matching_router)
FastApiMCP(
    kb_matching_app,
    include_operations=["list_kb_units", "match_kb_card"],
).mount_http()
app.mount("/api/v1/kb_matching", kb_matching_app)


# ── Sub-app: similar_incident_retrieval ─────────────────────────────────────

similar_incident_retrieval_app = _make_cors_app(
    title="similar_incident_retrieval_agent_mcps",
    description="MCP tools for finding similar past resolved tickets.",
)
similar_incident_retrieval_app.include_router(similar_incident_retrieval_router)
FastApiMCP(
    similar_incident_retrieval_app,
    include_operations=["find_similar_incidents"],
).mount_http()
app.mount("/api/v1/similar_incident_retrieval", similar_incident_retrieval_app)


# ── Sub-app: l0_self_service ─────────────────────────────────────────────────

l0_self_service_app = _make_cors_app(
    title="l0_self_service_agent_mcps",
    description="MCP tools for KB-card-grounded self-service chat with the requester.",
)
l0_self_service_app.include_router(l0_self_service_router)
FastApiMCP(
    l0_self_service_app,
    include_operations=["run_l0_chat", "record_outcome", "get_stats"],
).mount_http()
app.mount("/api/v1/l0_self_service", l0_self_service_app)


# ── Sub-app: l1_information_collector ───────────────────────────────────────

l1_information_collector_app = _make_cors_app(
    title="l1_information_collector_agent_mcps",
    description="MCP tools for checking a KB card's info_to_collect checklist against the ticket text.",
)
l1_information_collector_app.include_router(l1_information_collector_router)
FastApiMCP(
    l1_information_collector_app,
    include_operations=["collect_l1_info"],
).mount_http()
app.mount("/api/v1/l1_information_collector", l1_information_collector_app)


# ── Sub-app: policycenter_evidence_collector ────────────────────────────────

policycenter_evidence_collector_app = _make_cors_app(
    title="policycenter_evidence_collector_agent_mcps",
    description="[PARTIALLY IMPLEMENTED] MCP tools for loading demo PolicyCenter evidence fixtures.",
)
policycenter_evidence_collector_app.include_router(policycenter_evidence_collector_router)
FastApiMCP(
    policycenter_evidence_collector_app,
    include_operations=["collect_evidence"],
).mount_http()
app.mount("/api/v1/policycenter_evidence_collector", policycenter_evidence_collector_app)


# ── Sub-app: l2_diagnostic ───────────────────────────────────────────────────

l2_diagnostic_app = _make_cors_app(
    title="l2_diagnostic_agent_mcps",
    description="MCP tools for applying a KB card's diagnosis steps to collected evidence.",
)
l2_diagnostic_app.include_router(l2_diagnostic_router)
FastApiMCP(
    l2_diagnostic_app,
    include_operations=["diagnose"],
).mount_http()
app.mount("/api/v1/l2_diagnostic", l2_diagnostic_app)


# ── Sub-app: l3_remediation_proposal ────────────────────────────────────────

l3_remediation_proposal_app = _make_cors_app(
    title="l3_remediation_proposal_agent_mcps",
    description="MCP tools for drafting a Gosu remediation script and change-requirement document.",
)
l3_remediation_proposal_app.include_router(l3_remediation_proposal_router)
FastApiMCP(
    l3_remediation_proposal_app,
    include_operations=["author_remediation", "requirement_to_markdown"],
).mount_http()
app.mount("/api/v1/l3_remediation_proposal", l3_remediation_proposal_app)


# ── Sub-app: human_approval ──────────────────────────────────────────────────

human_approval_app = _make_cors_app(
    title="human_approval_agent_mcps",
    description="MCP tools for the deterministic HITL approval gate (no LLM, no DB).",
)
human_approval_app.include_router(human_approval_router)
FastApiMCP(
    human_approval_app,
    include_operations=["decide_approval"],
).mount_http()
app.mount("/api/v1/human_approval", human_approval_app)


# ── Sub-app: ticket_classification_triage ───────────────────────────────────

ticket_classification_triage_app = _make_cors_app(
    title="ticket_classification_triage_agent_mcps",
    description="MCP tools for classifying/triaging a ticket_records row against the controlled taxonomy.",
)
ticket_classification_triage_app.include_router(ticket_classification_triage_router)
FastApiMCP(
    ticket_classification_triage_app,
    include_operations=["classify_ticket_record"],
).mount_http()
app.mount("/api/v1/ticket_classification_triage", ticket_classification_triage_app)


# ── Sub-app: orchestrator_state ─────────────────────────────────────────────

orchestrator_state_app = _make_cors_app(
    title="orchestrator_state_mcps",
    description="The Orchestrator Agent's own state/persistence tools -- read/write a ticket's fix_runs record.",
)
orchestrator_state_app.include_router(orchestrator_state_router)
FastApiMCP(
    orchestrator_state_app,
    include_operations=["get_ticket_run", "save_l1_result", "save_l2_result", "save_l3_result"],
).mount_http()
app.mount("/api/v1/orchestrator_state", orchestrator_state_app)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "ticket_platform_backend_agents_mcp",
        "sub_apps": [
            "knowledge_ingestion_curation",
            "kb_matching",
            "similar_incident_retrieval",
            "l0_self_service",
            "l1_information_collector",
            "policycenter_evidence_collector",
            "l2_diagnostic",
            "l3_remediation_proposal",
            "human_approval",
            "ticket_classification_triage",
            "orchestrator_state",
        ],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("MCP_SERVER_PORT", "7900")))
