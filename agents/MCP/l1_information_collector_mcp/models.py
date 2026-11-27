from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class L1CollectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def require_text(self) -> "L1CollectRequest":
        if not (self.title or "").strip() and not (self.description or "").strip():
            raise ValueError("Provide a title or description")
        return self
