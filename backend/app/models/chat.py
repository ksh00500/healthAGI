from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class ChatConversation(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "chat_conversations"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mode: Mapped[str] = mapped_column(String(10), default="text", nullable=False)  # text | voice

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (Index("ix_conv_user_updated", "user_id", "updated_at"),)


class ChatMessage(UUIDPKMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "chat_messages"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # system|user|assistant|tool
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tool_args: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")


if TYPE_CHECKING:
    pass
