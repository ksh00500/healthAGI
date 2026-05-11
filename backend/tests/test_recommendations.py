from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.llm.mock_client import get_mock_client


async def _register(client: AsyncClient, email: str = "rec@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


_REC_PAYLOAD = {
    "workout_split": {
        "title": "오늘은 풀 데이",
        "body": "어깨 회복 중이라 등 위주 6세트 + 이두 4세트 권장.",
        "rationale": "어깨 36h 회복 남음, 등은 준비됨.",
    },
    "nutrition_focus": {
        "title": "단백질 부족",
        "body": "오늘 단백질 30g 추가 챙기기.",
        "rationale": "최근 3일 평균 단백질 90g/일.",
    },
    "recovery_check": {
        "title": "어깨 회복 중",
        "body": "고중량 푸시 운동은 피하세요.",
        "rationale": "회복 타이머 36시간 남음.",
    },
}


@pytest.mark.asyncio
async def test_generate_and_today(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # Initially empty.
    r = await client.get("/v1/recommendations/today", headers=h)
    assert r.status_code == 200
    assert r.json() == []

    get_mock_client().queue_json(_REC_PAYLOAD)
    r = await client.post("/v1/recommendations/generate", json={}, headers=h)
    assert r.status_code == 201, r.text
    cards = r.json()
    assert len(cards) == 3
    kinds = {c["kind"] for c in cards}
    assert kinds == {"workout_split", "nutrition_focus", "recovery_check"}
    assert any("단백질" in c["title"] for c in cards)

    # /today now returns the cached cards.
    r = await client.get("/v1/recommendations/today", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 3

    # Calling generate again without `force` returns existing (no new LLM call).
    mock = get_mock_client()
    calls_before = len(mock.calls)
    r = await client.post("/v1/recommendations/generate", json={}, headers=h)
    assert r.status_code == 201
    assert len(mock.calls) == calls_before  # mock not hit

    # With force, it does call the LLM and updates in place.
    mock.queue_json(
        {
            **_REC_PAYLOAD,
            "workout_split": {
                **_REC_PAYLOAD["workout_split"],
                "title": "수정된 제목",
            },
        }
    )
    r = await client.post(
        "/v1/recommendations/generate", json={"force": True}, headers=h
    )
    assert r.status_code == 201
    cards = r.json()
    titles = {c["title"] for c in cards}
    assert "수정된 제목" in titles


@pytest.mark.asyncio
async def test_timer_suggest_with_inline_sets(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    # Need a real exercise id from the seeded catalogue.
    r = await client.get("/v1/exercises", params={"q": "barbell_bench_press"}, headers=h)
    bench_id = r.json()[0]["id"]

    get_mock_client().queue_json(
        {
            "suggestions": [
                {
                    "muscle_group_id": "chest",
                    "hours": 60.0,
                    "intensity_score": 0.85,
                    "reason": "벤치프레스 4세트 평균 RPE 9",
                }
            ]
        }
    )

    r = await client.post(
        "/v1/timers/suggest",
        json={
            "sets": [
                {
                    "exercise_id": bench_id,
                    "set_index": 1,
                    "reps": 5,
                    "weight_kg": "90",
                    "rpe": "9",
                }
            ]
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    sug = r.json()["suggestions"]
    assert len(sug) == 1
    assert sug[0]["muscle_group_id"] == "chest"
    assert sug[0]["hours"] == 60.0


@pytest.mark.asyncio
async def test_timer_suggest_with_session_id(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get("/v1/exercises", params={"q": "squat"}, headers=h)
    squat_id = r.json()[0]["id"]

    r = await client.post(
        "/v1/workouts/sessions",
        json={
            "sets": [
                {
                    "exercise_id": squat_id,
                    "set_index": 1,
                    "reps": 5,
                    "weight_kg": "100",
                    "rpe": "8",
                }
            ]
        },
        headers=h,
    )
    sid = r.json()["id"]

    get_mock_client().queue_json(
        {
            "suggestions": [
                {"muscle_group_id": "quads", "hours": 72.0, "intensity_score": 0.8},
                # Unknown muscle group should be filtered out.
                {"muscle_group_id": "bogus", "hours": 1.0, "intensity_score": 0.1},
            ]
        }
    )

    r = await client.post(
        "/v1/timers/suggest", json={"session_id": sid}, headers=h
    )
    assert r.status_code == 200
    sug = r.json()["suggestions"]
    assert len(sug) == 1
    assert sug[0]["muscle_group_id"] == "quads"


@pytest.mark.asyncio
async def test_timer_suggest_requires_input(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/v1/timers/suggest", json={}, headers=h)
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_timer_suggest_isolation(client: AsyncClient) -> None:
    a = await _register(client, "a@x.com")
    b = await _register(client, "b@x.com")
    r = await client.get(
        "/v1/exercises",
        params={"q": "barbell_bench_press"},
        headers={"Authorization": f"Bearer {a}"},
    )
    bench_id = r.json()[0]["id"]
    r = await client.post(
        "/v1/workouts/sessions",
        json={"sets": [{"exercise_id": bench_id, "set_index": 1, "reps": 5}]},
        headers={"Authorization": f"Bearer {a}"},
    )
    sid = r.json()["id"]
    # User b cannot suggest against a's session.
    r = await client.post(
        "/v1/timers/suggest",
        json={"session_id": sid},
        headers={"Authorization": f"Bearer {b}"},
    )
    assert r.status_code == 404
