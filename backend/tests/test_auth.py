from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_flow(client: AsyncClient) -> None:
    r = await client.post(
        "/v1/auth/register",
        json={"email": "a@b.com", "password": "supersecret"},
    )
    assert r.status_code == 201, r.text
    tokens = r.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    # duplicate
    r = await client.post(
        "/v1/auth/register",
        json={"email": "a@b.com", "password": "supersecret"},
    )
    assert r.status_code == 409

    # wrong password
    r = await client.post(
        "/v1/auth/login",
        json={"email": "a@b.com", "password": "wrongpassword"},
    )
    assert r.status_code == 401

    # right password
    r = await client.post(
        "/v1/auth/login",
        json={"email": "a@b.com", "password": "supersecret"},
    )
    assert r.status_code == 200
    tokens2 = r.json()

    # me
    r = await client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {tokens2['access_token']}"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == "a@b.com"

    # refresh
    r = await client.post(
        "/v1/auth/refresh", json={"refresh_token": tokens2["refresh_token"]}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


@pytest.mark.asyncio
async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/v1/auth/me")
    assert r.status_code == 401
