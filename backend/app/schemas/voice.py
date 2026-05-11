from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class VoiceTurnResponse(BaseModel):
    conversation_id: UUID
    user_message_id: UUID
    assistant_message_id: UUID
    transcript: str
    reply_text: str
    audio_b64: str
    audio_mime: str
    audio_sample_rate: int
    stt_language: str | None
    stt_duration_s: float | None
    tokens_in: int | None = None
    tokens_out: int | None = None
