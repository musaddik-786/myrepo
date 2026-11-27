from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class SimilarIncidentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    title: str | None = None
    description: str | None = None
    module: str | None = None
    severity: str | None = None
    created: str | None = None

    @model_validator(mode="after")
    def require_text(self) -> "SimilarIncidentRequest":
        if not (self.title or "").strip() and not (self.description or "").strip():
            raise ValueError("Provide a title or description")
        return self
