from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": "m@x.com", "password": "supersecret"}
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_meal_create_with_totals(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/meals",
        json={
            "eaten_at": datetime.now(UTC).isoformat(),
            "meal_type": "lunch",
            "raw_input": "닭가슴살 200g + 밥 1공기",
            "items": [
                {"name": "닭가슴살", "serving_g": "200", "kcal": "330", "protein_g": "62", "carbs_g": "0", "fat_g": "7"},
                {"name": "백미밥",   "serving_g": "210", "kcal": "300", "protein_g": "6",  "carbs_g": "67", "fat_g": "1"},
            ],
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    meal = r.json()
    assert float(meal["total_kcal"]) == 630.0
    assert float(meal["total_protein_g"]) == 68.0
    assert len(meal["items"]) == 2


@pytest.mark.asyncio
async def test_meal_filter_by_day(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    today = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    yesterday = datetime(2026, 5, 10, 12, 0, tzinfo=UTC)
    for ts in (today, yesterday):
        r = await client.post(
            "/v1/meals",
            json={"eaten_at": ts.isoformat(), "items": [{"name": "test", "kcal": "100"}]},
            headers=h,
        )
        assert r.status_code == 201

    r = await client.get("/v1/meals", params={"day": "2026-05-11"}, headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_meal_update_items_recomputes_totals(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/meals",
        json={"items": [{"name": "a", "kcal": "100"}]},
        headers=h,
    )
    meal_id = r.json()["id"]
    r = await client.patch(
        f"/v1/meals/{meal_id}",
        json={"items": [{"name": "a", "kcal": "200"}, {"name": "b", "kcal": "50"}]},
        headers=h,
    )
    assert r.status_code == 200
    assert float(r.json()["total_kcal"]) == 250.0

    r = await client.delete(f"/v1/meals/{meal_id}", headers=h)
    assert r.status_code == 204
