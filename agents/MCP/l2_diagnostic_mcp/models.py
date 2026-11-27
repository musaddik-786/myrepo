from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class L2DiagnoseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    card: dict[str, Any]  # the matched KB card content, from l1_information_collector_mcp (or kb_matching_mcp)
    evidence: dict[str, Any]  # from policycenter_evidence_collector_mcp
