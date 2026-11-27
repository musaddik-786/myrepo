from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

VALID_SOURCES = {"tickets", "chat_rca", "release_notes", "runbooks"}


class IngestionRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[str] | None = Field(
        default=None,
        description="Subset of {tickets, chat_rca, release_notes, runbooks} to refresh. "
                    "Omit to refresh all 4 (backend/pipeline.py's default behavior).",
    )
    force: bool = Field(
        default=False,
        description="Re-tag and re-embed every selected record even if unchanged since the last run.",
    )


class IngestClosedTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    resolution_type: str
    notes: str
