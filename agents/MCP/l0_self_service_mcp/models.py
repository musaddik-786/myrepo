from __future__ import annotations

from pydantic import BaseModel, ConfigDict

OUTCOMES = ("open", "resolved", "ticket_created")


class ChatMessage(BaseModel):
    role: str
    content: str


class L0ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage]
    session_id: str | None = None


class L0OutcomeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    outcome: str
