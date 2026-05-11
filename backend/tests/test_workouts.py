from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "w@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_exercise_search(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get("/v1/exercises", headers=h)
    assert r.status_code == 200
    assert len(r.json()) >= 10

    r = await client.get("/v1/exercises", params={"q": "벤치"}, headers=h)
    assert r.status_code == 200
    canon = {e["canonical_name"] for e in r.json()}
    assert "barbell_bench_press" in canon

    r = await client.get("/v1/exercises", params={"q": "squat"}, headers=h)
    canon = {e["canonical_name"] for e in r.json()}
    assert "barbell_squat" in canon


@pytest.mark.asyncio
async def test_workout_session_crud(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # pick the bench press id
    r = await client.get("/v1/exercises", params={"q": "barbell_bench_press"}, headers=h)
    bench_id = r.json()[0]["id"]
    r = await client.get("/v1/exercises", params={"q": "squat"}, headers=h)
    squat_id = r.json()[0]["id"]

    payload = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "notes": "push day",
        "sets": [
            {"exercise_id": bench_id, "set_index": 1, "reps": 8, "weight_kg": "60.0"},
            {"exercise_id": bench_id, "set_index": 2, "reps": 8, "weight_kg": "65.0", "rpe": "7.5"},
            {"exercise_id": squat_id, "set_index": 1, "reps": 5, "weight_kg": "100", "is_warmup": False},
        ],
    }
    r = await client.post("/v1/workouts/sessions", json=payload, headers=h)
    assert r.status_code == 201, r.text
    ws = r.json()
    assert len(ws["sets"]) == 3
    sid = ws["id"]

    r = await client.get("/v1/workouts/sessions", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Patch — replace sets with 2 entries.
    r = await client.patch(
        f"/v1/workouts/sessions/{sid}",
        json={
            "notes": "edited",
            "sets": [
                {"exercise_id": bench_id, "set_index": 1, "reps": 10, "weight_kg": "55.0"},
                {"exercise_id": bench_id, "set_index": 2, "reps": 8, "weight_kg": "60.0"},
            ],
        },
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["notes"] == "edited"
    assert len(r.json()["sets"]) == 2

    r = await client.delete(f"/v1/workouts/sessions/{sid}", headers=h)
    assert r.status_code == 204
    r = await client.get("/v1/workouts/sessions", headers=h)
    assert r.json() == []


@pytest.mark.asyncio
async def test_workout_unknown_exercise(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    payload = {
        "sets": [
            {
                "exercise_id": "00000000-0000-0000-0000-000000000000",
                "set_index": 1,
                "reps": 5,
                "weight_kg": "50",
            }
        ]
    }
    r = await client.post("/v1/workouts/sessions", json=payload, headers=h)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_custom_exercise(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/exercises",
        json={
            "canonical_name": "cable_crossover",
            "display_name_ko": "케이블 크로스오버",
            "primary_muscle_group_id": "chest",
            "aliases": ["크로스오버"],
        },
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["canonical_name"] == "cable_crossover"

    r = await client.get("/v1/exercises", params={"q": "크로스오버"}, headers=h)
    assert any(e["canonical_name"] == "cable_crossover" for e in r.json())
