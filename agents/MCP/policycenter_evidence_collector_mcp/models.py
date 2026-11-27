from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class EvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str  # the matched KB card's unit_id (see kb_matching_mcp or l1_information_collector_mcp)
