from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import (
    ChatConversationDetail,
    ChatConversationRead,
    ConversationCreate,
    MessageCreate,
)
from app.services.llm import get_llm_client
from app.services.llm.base import ChatTurn
from app.services.llm.prompts import build_system_prompt, turns_from_history

router = APIRouter(prefix="/chat", tags=["chat"])


def _detail_stmt(user_id: UUID, conv_id: UUID):
    return (
        select(ChatConversation)
        .options(selectinload(ChatConversation.messages))
        .where(
            ChatConversation.id == conv_id,
            ChatConversation.user_id == user_id,
            ChatConversation.deleted_at.is_(None),
        )
    )


@router.get("/conversations", response_model=list[ChatConversationRead])
async def list_conversations(
    user: CurrentUser, session: SessionDep
) -> list[ChatConversation]:
    rows = await session.scalars(
        select(ChatConversation)
        .where(
            ChatConversation.user_id == user.id,
            ChatConversation.deleted_at.is_(None),
        )
        .order_by(ChatConversation.updated_at.desc())
    )
    return list(rows)


@router.post(
    "/conversations",
    response_model=ChatConversationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate, user: CurrentUser, session: SessionDep
) -> ChatConversation:
    conv = ChatConversation(user_id=user.id, title=payload.title, mode=payload.mode)
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv


@router.get(
    "/conversations/{conv_id}", response_model=ChatConversationDetail
)
async def get_conversation(
    conv_id: UUID, user: CurrentUser, session: SessionDep
) -> ChatConversation:
    conv = await session.scalar(_detail_stmt(user.id, conv_id))
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    return conv


@router.delete(
    "/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conv_id: UUID, user: CurrentUser, session: SessionDep
) -> None:
    conv = await session.scalar(_detail_stmt(user.id, conv_id))
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")
    conv.deleted_at = datetime.now(timezone.utc)
    await session.commit()


def _sse(event: str, payload: dict) -> bytes:
    """Encode a single Server-Sent Event with JSON payload + named event."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


@router.post("/conversations/{conv_id}/messages")
async def post_message(
    conv_id: UUID,
    payload: MessageCreate,
    user: CurrentUser,
    session: SessionDep,
) -> StreamingResponse:
    """Append a user message, stream the assistant reply via SSE.

    Events:
      - meta:   {assistant_message_id, model}
      - token:  {text}
      - done:   {content, tokens_in, tokens_out}
      - error:  {message}
    """
    conv = await session.scalar(_detail_stmt(user.id, conv_id))
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "conversation not found")

    # Persist user message first.
    user_msg = ChatMessage(conversation_id=conv.id, role="user", content=payload.content)
    session.add(user_msg)
    await session.commit()

    system_prompt = await build_system_prompt(session, user)

    # Refresh history including the new user message.
    history_rows = await session.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at)
    )
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    turns: list[ChatTurn] = [ChatTurn(role="system", content=system_prompt)]
    turns.extend(turns_from_history(history))

    llm = get_llm_client()
    settings = get_settings()
    model = settings.llm_text_model

    # Pre-create empty assistant message so the id is available immediately.
    assistant_msg = ChatMessage(
        conversation_id=conv.id, role="assistant", content="", model=model
    )
    session.add(assistant_msg)
    await session.commit()
    await session.refresh(assistant_msg)
    assistant_id = assistant_msg.id

    async def stream() -> AsyncIterator[bytes]:
        nonlocal assistant_msg
        yield _sse(
            "meta", {"assistant_message_id": str(assistant_id), "model": model}
        )
        collected: list[str] = []
        eval_count: int | None = None
        prompt_eval_count: int | None = None
        try:
            async for chunk in llm.chat_stream(turns, model=model):
                if chunk.kind == "token":
                    collected.append(chunk.text)
                    yield _sse("token", {"text": chunk.text})
                elif chunk.kind == "done":
                    eval_count = chunk.eval_count
                    prompt_eval_count = chunk.prompt_eval_count
                    break
                elif chunk.kind == "error":
                    yield _sse("error", {"message": chunk.error or "unknown error"})
                    return
        except Exception as e:  # noqa: BLE001
            yield _sse("error", {"message": str(e)})
            return

        full = "".join(collected)
        # Reload the row in a fresh session-friendly way: re-fetch by id.
        msg = await session.scalar(
            select(ChatMessage).where(ChatMessage.id == assistant_id)
        )
        if msg is not None:
            msg.content = full
            msg.tokens_in = prompt_eval_count
            msg.tokens_out = eval_count
            await session.commit()

        yield _sse(
            "done",
            {
                "content": full,
                "tokens_in": prompt_eval_count,
                "tokens_out": eval_count,
            },
        )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
