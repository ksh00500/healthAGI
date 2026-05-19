from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient) -> str:
    r = await client.post(
        "/v1/auth/register",
        json={"email": "p@x.com", "password": "supersecret"},
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_profile_roundtrip(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.get("/v1/profile", headers=h)
    assert r.status_code == 200
    assert r.json()["locale"] == "ko-KR"

    r = await client.put(
        "/v1/profile",
        json={"display_name": "Tester", "height_cm": "178.0", "goals": "hypertrophy"},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Tester"
    assert float(body["height_cm"]) == 178.0


@pytest.mark.asyncio
async def test_body_metric_crud(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/v1/profile/body-metrics",
        json={
            "measured_at": datetime.now(UTC).isoformat(),
            "weight_kg": "76.4",
            "sleep_hours": "7.5",
        },
        headers=h,
    )
    assert r.status_code == 201
    metric = r.json()

    r = await client.get("/v1/profile/body-metrics", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.patch(
        f"/v1/profile/body-metrics/{metric['id']}",
        json={"weight_kg": "76.0"},
        headers=h,
    )
    assert r.status_code == 200
    assert float(r.json()["weight_kg"]) == 76.0

    r = await client.delete(f"/v1/profile/body-metrics/{metric['id']}", headers=h)
    assert r.status_code == 204
