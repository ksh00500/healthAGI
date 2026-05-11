from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.llm.mock_client import get_mock_client


async def _register(client: AsyncClient) -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": "parse@x.com", "password": "supersecret"}
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_workout_parse(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    get_mock_client().queue_json(
        {
            "exercises": [
                {
                    "name": "바벨 벤치프레스",
                    "sets": [
                        {"set_index": 1, "reps": 5, "weight_kg": 80, "is_warmup": False},
                        {"set_index": 2, "reps": 5, "weight_kg": 80, "is_warmup": False},
                    ],
                },
                {
                    "name": "스쿼트",
                    "sets": [
                        {"set_index": 1, "reps": 5, "weight_kg": 120, "is_warmup": False}
                    ],
                },
            ],
            "notes": None,
        }
    )

    r = await client.post(
        "/v1/workouts/parse",
        json={"text": "벤치 80kg 5,5 / 스쿼트 120 x 5"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["exercises"]) == 2
    bench = data["exercises"][0]
    # Should match the canonical seed (barbell_bench_press) on "벤치프레스".
    assert bench["matched_exercise_id"] is not None
    assert len(bench["sets"]) == 2
    assert bench["sets"][0]["set_index"] == 1
    assert float(bench["sets"][0]["weight_kg"]) == 80.0


@pytest.mark.asyncio
async def test_meal_parse(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    get_mock_client().queue_json(
        {
            "items": [
                {
                    "name": "닭가슴살",
                    "serving_g": 200,
                    "kcal": 330,
                    "protein_g": 62,
                    "carbs_g": 0,
                    "fat_g": 7,
                    "confidence": 0.85,
                },
                {
                    "name": "백미밥",
                    "serving_g": 210,
                    "kcal": 300,
                    "protein_g": 6,
                    "carbs_g": 67,
                    "fat_g": 1,
                    "confidence": 0.9,
                },
            ]
        }
    )

    r = await client.post(
        "/v1/meals/parse",
        json={"text": "닭가슴살 200g + 밥 1공기"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 2
    assert items[0]["name"] == "닭가슴살"
    assert float(items[0]["protein_g"]) == 62.0


@pytest.mark.asyncio
async def test_parse_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/v1/workouts/parse", json={"text": "벤치 80x5"})
    assert r.status_code == 401
    r = await client.post("/v1/meals/parse", json={"text": "밥"})
    assert r.status_code == 401
