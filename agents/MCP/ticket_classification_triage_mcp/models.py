from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ClassifyTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
