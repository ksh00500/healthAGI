from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "u@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    assert r.status_code == 201
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_muscle_groups(client: AsyncClient) -> None:
    r = await client.get("/v1/muscle-groups")
    assert r.status_code == 200
    groups = r.json()
    ids = {g["id"] for g in groups}
    assert "chest" in ids
    assert "quads" in ids
    chest = next(g for g in groups if g["id"] == "chest")
    assert chest["default_recovery_hours"] == 48


@pytest.mark.asyncio
async def test_timer_crud(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # Create using muscle group default duration.
    r = await client.post(
        "/v1/timers",
        json={"muscle_group_id": "chest"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["muscle_group_id"] == "chest"
    assert t["duration_minutes"] == 48 * 60

    # Idempotent retry with client_op_id.
    op_id = "11111111-1111-1111-1111-111111111111"
    r = await client.post(
        "/v1/timers",
        json={"muscle_group_id": "back", "duration_minutes": 60, "client_op_id": op_id},
        headers=h,
    )
    assert r.status_code == 201
    first = r.json()
    r2 = await client.post(
        "/v1/timers",
        json={"muscle_group_id": "back", "duration_minutes": 60, "client_op_id": op_id},
        headers=h,
    )
    assert r2.status_code in (200, 201)
    assert r2.json()["id"] == first["id"]

    # List current — should have chest + back.
    r = await client.get("/v1/timers/current", headers=h)
    assert r.status_code == 200
    current = r.json()
    mg_ids = {t["muscle_group_id"] for t in current}
    assert {"chest", "back"} <= mg_ids

    # Patch duration.
    chest_id = next(t["id"] for t in current if t["muscle_group_id"] == "chest")
    r = await client.patch(
        f"/v1/timers/{chest_id}",
        json={"duration_minutes": 24 * 60},
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["duration_minutes"] == 24 * 60

    # Soft delete.
    r = await client.delete(f"/v1/timers/{chest_id}", headers=h)
    assert r.status_code == 204
    r = await client.get("/v1/timers/current", headers=h)
    assert "chest" not in {t["muscle_group_id"] for t in r.json()}


@pytest.mark.asyncio
async def test_timer_user_isolation(client: AsyncClient) -> None:
    t1 = await _register(client, "one@x.com")
    t2 = await _register(client, "two@x.com")
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    r = await client.post("/v1/timers", json={"muscle_group_id": "biceps"}, headers=h1)
    assert r.status_code == 201
    timer_id = r.json()["id"]

    # User 2 can't read/modify user 1's timer.
    r = await client.get("/v1/timers/current", headers=h2)
    assert r.json() == []
    r = await client.patch(
        f"/v1/timers/{timer_id}", json={"duration_minutes": 10}, headers=h2
    )
    assert r.status_code == 404
    r = await client.delete(f"/v1/timers/{timer_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_timer_explicit_start_time(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    start = datetime(2026, 1, 1, 12, 0, tzinfo=UTC).isoformat()
    r = await client.post(
        "/v1/timers",
        json={
            "muscle_group_id": "quads",
            "start_time": start,
            "duration_minutes": 90,
            "intensity_score": "0.85",
            "notes": "heavy squat day",
        },
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["duration_minutes"] == 90
    assert body["notes"] == "heavy squat day"
