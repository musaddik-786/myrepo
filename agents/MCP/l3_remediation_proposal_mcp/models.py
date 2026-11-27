from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class L3AuthorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    title: str | None = None
    description: str | None = None
    card: dict[str, Any]  # from l1_information_collector_mcp (or kb_matching_mcp)
    l2: dict[str, Any]  # from l2_diagnostic_mcp -- must have needs_data_fix=true
    evidence: dict[str, Any]  # from policycenter_evidence_collector_mcp


class RequirementMarkdownRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: dict[str, Any]
