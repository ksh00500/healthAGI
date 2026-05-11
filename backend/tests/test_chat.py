from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.llm.mock_client import get_mock_client


async def _register(client: AsyncClient, email: str = "chat@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_conversation_crud(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/v1/chat/conversations", json={"title": "첫 대화"}, headers=h
    )
    assert r.status_code == 201, r.text
    conv = r.json()
    assert conv["title"] == "첫 대화"
    cid = conv["id"]

    r = await client.get("/v1/chat/conversations", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.get(f"/v1/chat/conversations/{cid}", headers=h)
    assert r.status_code == 200
    assert r.json()["messages"] == []

    r = await client.delete(f"/v1/chat/conversations/{cid}", headers=h)
    assert r.status_code == 204
    r = await client.get("/v1/chat/conversations", headers=h)
    assert r.json() == []


@pytest.mark.asyncio
async def test_message_streams_and_persists(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # Conversation
    r = await client.post("/v1/chat/conversations", json={}, headers=h)
    cid = r.json()["id"]

    # Prime the mock LLM
    get_mock_client().queue("좋아요, 회복 상태를 보면 가슴 운동이 가능합니다.")

    async with client.stream(
        "POST",
        f"/v1/chat/conversations/{cid}/messages",
        json={"content": "오늘 뭐 운동할까?"},
        headers=h,
    ) as r:
        assert r.status_code == 200
        events: list[str] = []
        async for line in r.aiter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
        assert "meta" in events
        assert "token" in events
        assert "done" in events

    # User + assistant messages persisted.
    r = await client.get(f"/v1/chat/conversations/{cid}", headers=h)
    msgs = r.json()["messages"]
    assert len(msgs) == 2
    roles = [m["role"] for m in msgs]
    assert roles == ["user", "assistant"]
    assert "가슴 운동" in msgs[1]["content"]


@pytest.mark.asyncio
async def test_message_includes_system_context(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # Start a chest timer so the system prompt reflects recovery state.
    await client.post("/v1/timers", json={"muscle_group_id": "chest"}, headers=h)

    r = await client.post("/v1/chat/conversations", json={}, headers=h)
    cid = r.json()["id"]

    mock = get_mock_client()
    mock.queue("OK")

    async with client.stream(
        "POST",
        f"/v1/chat/conversations/{cid}/messages",
        json={"content": "test"},
        headers=h,
    ) as r:
        async for _ in r.aiter_lines():
            pass

    # The mock recorded the call; the first message should be the system prompt
    # and it should mention the chest recovery line.
    assert mock.calls, "mock LLM was not called"
    system_turn = mock.calls[-1][0]
    assert system_turn.role == "system"
    assert "회복 상태" in system_turn.content
    assert "가슴" in system_turn.content
