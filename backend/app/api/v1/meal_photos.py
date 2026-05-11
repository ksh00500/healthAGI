from __future__ import annotations

import base64
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models.meal import MealPhoto
from app.services.llm import get_llm_client
from app.services.storage import get_storage

router = APIRouter(prefix="/meals/photo", tags=["meal-photos"])

MAX_PHOTO_BYTES = 8 * 1024 * 1024  # 8 MB — client should compress to ~150 KB anyway.

_VISION_SYSTEM = (
    "당신은 식단 사진을 분석하는 영양 전문가입니다. "
    "사진의 음식들을 식별하고, 한국 식품 영양정보를 기준으로 "
    "각 항목의 1인분 추정량과 매크로를 구조화 JSON으로 반환합니다."
)

_VISION_USER = (
    "이 사진의 음식을 분석해 JSON 객체로 반환하세요.\n"
    "스키마: {\n"
    '  "items": [\n'
    '    {"name": "음식명", "serving_g": 200, "kcal": 330, '
    '"protein_g": 30, "carbs_g": 40, "fat_g": 10, "confidence": 0.8}\n'
    "  ]\n"
    "}\n"
    "규칙: 1) 한국 식품은 한글, 외국 식품은 표준 명칭.\n"
    "2) 양이 명확하지 않으면 한국 1인분 기준으로 추정.\n"
    "3) confidence는 0~1 사이 신뢰도.\n"
    "4) 모르면 해당 영양소는 null."
)


class PhotoAnalyzeItem(BaseModel):
    name: str
    serving_g: Decimal | None = None
    kcal: Decimal | None = None
    protein_g: Decimal | None = None
    carbs_g: Decimal | None = None
    fat_g: Decimal | None = None
    confidence: Decimal | None = None


class PhotoAnalyzeResponse(BaseModel):
    storage_key: str
    items: list[PhotoAnalyzeItem]
    presigned_url: str | None = None


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


def _ext_for(mime: str) -> str:
    if "png" in mime:
        return "png"
    if "webp" in mime:
        return "webp"
    if "heic" in mime or "heif" in mime:
        return "heic"
    return "jpg"


@router.post("/analyze", response_model=PhotoAnalyzeResponse)
async def analyze_photo(
    user: CurrentUser,
    session: SessionDep,
    photo: UploadFile = File(..., description="meal photo (jpeg/png/webp)"),
) -> PhotoAnalyzeResponse:
    """Upload a meal photo, run vision LLM, return proposed items + storage_key.

    The client typically edits the proposed items, then calls POST /meals
    with `photo_storage_key` set so the photo is attached to the resulting meal.
    """
    raw = await photo.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty photo")
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"photo too large ({len(raw)} > {MAX_PHOTO_BYTES}); compress on device",
        )
    mime = photo.content_type or "image/jpeg"
    ext = _ext_for(mime)
    storage_key = f"users/{user.id}/meals/{uuid4()}.{ext}"

    storage = get_storage()
    await storage.put_object(storage_key, raw, content_type=mime)

    llm = get_llm_client()
    settings = get_settings()
    try:
        raw_response = await llm.complete_vision_json(
            _VISION_SYSTEM,
            _VISION_USER,
            raw,
            model=settings.llm_vision_model,
        )
    except Exception as e:  # noqa: BLE001
        # Keep the uploaded blob (user can retry analyze on the same key later).
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"vision LLM failed: {e}"
        ) from e

    items_raw = raw_response.get("items") or []
    items: list[PhotoAnalyzeItem] = []
    for it in items_raw:
        items.append(
            PhotoAnalyzeItem(
                name=(it.get("name") or "").strip() or "unknown",
                serving_g=_dec(it.get("serving_g")),
                kcal=_dec(it.get("kcal")),
                protein_g=_dec(it.get("protein_g")),
                carbs_g=_dec(it.get("carbs_g")),
                fat_g=_dec(it.get("fat_g")),
                confidence=_dec(it.get("confidence")),
            )
        )

    # Persist the MealPhoto so client can attach via /meals POST.
    photo_row = MealPhoto(
        user_id=user.id,
        meal_id=None,
        storage_key=storage_key,
        uploaded_at=datetime.now(timezone.utc),
        vision_model=settings.llm_vision_model,
        vision_raw_response=raw_response,
    )
    session.add(photo_row)
    await session.commit()

    return PhotoAnalyzeResponse(
        storage_key=storage_key,
        items=items,
        presigned_url=storage.presigned_get_url(storage_key),
    )


class PhotoFetchResponse(BaseModel):
    storage_key: str
    content_type: str
    data_b64: str


@router.get("/{storage_key:path}", response_model=PhotoFetchResponse)
async def fetch_photo(
    storage_key: str, user: CurrentUser, session: SessionDep
) -> PhotoFetchResponse:
    """Return a meal photo as base64 (for local storage where no presigned URL).

    For MinIO with a presigned URL, the client should use that URL directly.
    """
    row = await session.scalar(
        select(MealPhoto).where(
            MealPhoto.storage_key == storage_key,
            MealPhoto.user_id == user.id,
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "photo not found")

    storage = get_storage()
    try:
        data = await storage.get_object(storage_key)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "blob missing") from e
    mime = "image/jpeg"
    if storage_key.endswith(".png"):
        mime = "image/png"
    elif storage_key.endswith(".webp"):
        mime = "image/webp"
    return PhotoFetchResponse(
        storage_key=storage_key,
        content_type=mime,
        data_b64=base64.b64encode(data).decode("ascii"),
    )
