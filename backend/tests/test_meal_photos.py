from __future__ import annotations

import base64

import pytest
from httpx import AsyncClient

from app.services.llm.mock_client import get_mock_client
from app.services.storage.memory_storage import get_memory_storage


async def _register(client: AsyncClient, email: str = "photo@x.com") -> str:
    r = await client.post(
        "/v1/auth/register", json={"email": email, "password": "supersecret"}
    )
    return r.json()["access_token"]


_FAKE_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    + b"\x00" * 200
    + b"\xff\xd9"
)


@pytest.mark.asyncio
async def test_analyze_photo_returns_items_and_persists(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}

    get_mock_client().queue_vision(
        {
            "items": [
                {
                    "name": "닭가슴살 구이",
                    "serving_g": 200,
                    "kcal": 330,
                    "protein_g": 62,
                    "carbs_g": 0,
                    "fat_g": 7,
                    "confidence": 0.85,
                },
                {
                    "name": "현미밥",
                    "serving_g": 210,
                    "kcal": 320,
                    "protein_g": 7,
                    "carbs_g": 65,
                    "fat_g": 2,
                    "confidence": 0.78,
                },
            ]
        }
    )

    files = {"photo": ("meal.jpg", _FAKE_JPEG, "image/jpeg")}
    r = await client.post("/v1/meals/photo/analyze", headers=h, files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["storage_key"].endswith(".jpg")
    assert len(body["items"]) == 2
    assert body["items"][0]["name"] == "닭가슴살 구이"

    # Storage actually received the bytes.
    storage = get_memory_storage()
    assert body["storage_key"] in storage.all_keys()
    assert (await storage.get_object(body["storage_key"])) == _FAKE_JPEG


@pytest.mark.asyncio
async def test_analyze_then_save_attaches_photo(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    get_mock_client().queue_vision(
        {"items": [{"name": "오트밀", "serving_g": 80, "kcal": 300, "protein_g": 12}]}
    )

    r = await client.post(
        "/v1/meals/photo/analyze",
        headers=h,
        files={"photo": ("m.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    storage_key = r.json()["storage_key"]

    # Save meal with the photo_storage_key.
    r = await client.post(
        "/v1/meals",
        json={
            "meal_type": "breakfast",
            "raw_input": "사진 분석",
            "items": [{"name": "오트밀", "kcal": "300", "protein_g": "12"}],
            "photo_storage_key": storage_key,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    meal = r.json()
    assert meal["source"] == "photo"

    # Re-attaching the same photo to another meal should now 409.
    r = await client.post(
        "/v1/meals",
        json={"items": [{"name": "x", "kcal": "10"}], "photo_storage_key": storage_key},
        headers=h,
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_unknown_photo_key_rejected(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/meals",
        json={"items": [{"name": "x", "kcal": "10"}], "photo_storage_key": "missing"},
        headers=h,
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_fetch_photo_returns_blob(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    get_mock_client().queue_vision({"items": []})
    r = await client.post(
        "/v1/meals/photo/analyze",
        headers=h,
        files={"photo": ("p.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    key = r.json()["storage_key"]

    r = await client.get(f"/v1/meals/photo/{key}", headers=h)
    assert r.status_code == 200, r.text
    data = base64.b64decode(r.json()["data_b64"])
    assert data == _FAKE_JPEG


@pytest.mark.asyncio
async def test_photo_isolation_between_users(client: AsyncClient) -> None:
    a = await _register(client, "a@x.com")
    b = await _register(client, "b@x.com")
    get_mock_client().queue_vision({"items": []})
    r = await client.post(
        "/v1/meals/photo/analyze",
        headers={"Authorization": f"Bearer {a}"},
        files={"photo": ("p.jpg", _FAKE_JPEG, "image/jpeg")},
    )
    key = r.json()["storage_key"]
    # b cannot fetch a's photo.
    r = await client.get(
        f"/v1/meals/photo/{key}",
        headers={"Authorization": f"Bearer {b}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_empty_photo_rejected(client: AsyncClient) -> None:
    token = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/v1/meals/photo/analyze",
        headers=h,
        files={"photo": ("p.jpg", b"", "image/jpeg")},
    )
    assert r.status_code == 400
