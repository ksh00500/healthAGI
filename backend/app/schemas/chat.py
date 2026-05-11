from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None
    tool_name: str | None
    tool_args: dict[str, Any] | None
    tool_result: dict[str, Any] | None
    model: str | None
    created_at: datetime


class ChatConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    mode: Literal["text", "voice"]
    created_at: datetime
    updated_at: datetime


class ChatConversationDetail(ChatConversationRead):
    messages: list[ChatMessageRead]


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    mode: Literal["text", "voice"] = "text"


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
