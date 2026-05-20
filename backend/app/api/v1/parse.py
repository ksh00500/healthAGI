from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.models.exercise import Exercise
from app.services.llm import get_llm_client
from app.services.llm.base import ChatTurn

router = APIRouter(tags=["parse"])

_MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB


class ParseTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


# --- Workouts ---


class ParsedSet(BaseModel):
    set_index: int
    reps: int | None = None
    weight_kg: Decimal | None = None
    rpe: Decimal | None = None
    is_warmup: bool = False


class ParsedExercise(BaseModel):
    matched_exercise_id: str | None = None
    name: str
    sets: list[ParsedSet]


class ParsedWorkout(BaseModel):
    exercises: list[ParsedExercise]
    notes: str | None = None
    raw: str


_WORKOUT_PROMPT = (
    "사용자가 입력한 자유 텍스트 운동 기록을 구조화 JSON으로 변환합니다.\n"
    "입력 예: '벤치 80kg 5,5,4 / 스쿼트 120 x 5 x 3 / 데드 100 1세트'\n"
    "출력은 반드시 다음 스키마의 JSON 객체:\n"
    "{\n"
    '  "exercises": [\n'
    '    {"name": "<한국어 또는 영어 운동명>", "sets": [\n'
    '       {"set_index": 1, "reps": 5, "weight_kg": 80.0, "rpe": null, "is_warmup": false}\n'
    "    ]}\n"
    "  ],\n"
    '  "notes": null\n'
    "}\n"
    "규칙: 1) 단위(kg, lbs)에 주의. lbs는 kg로 환산(1 lb = 0.4536 kg).\n"
    "2) set_index는 1부터 시작.\n"
    "3) 워밍업 표기('warmup','w/u')가 있으면 is_warmup=true.\n"
    "4) 수치가 명확히 없으면 null로 둘 것.\n"
    "5) 운동명은 입력에 등장한 그대로 자연스럽게."
)


def _decimal_or_none(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


def _int_or_none(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


async def _match_exercise(session: AsyncSession, name: str) -> str | None:
    if not name:
        return None
    needle = f"%{name.lower()}%"
    stmt = select(Exercise).where(
        (Exercise.canonical_name.ilike(needle))
        | (Exercise.display_name_ko.ilike(needle))
        | (Exercise.display_name_en.ilike(needle))
    ).limit(1)
    ex = await session.scalar(stmt)
    return str(ex.id) if ex else None


@router.post("/workouts/parse", response_model=ParsedWorkout)
async def parse_workout(
    payload: ParseTextRequest, _user: CurrentUser, session: SessionDep
) -> ParsedWorkout:
    llm = get_llm_client()
    try:
        data = await llm.complete_json(
            [
                ChatTurn(role="system", content=_WORKOUT_PROMPT),
                ChatTurn(role="user", content=payload.text),
            ],
            model=get_settings().llm_parse_model,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"LLM parse failed: {e}"
        ) from e

    exercises_raw = data.get("exercises") or []
    out_exercises: list[ParsedExercise] = []
    for ex_raw in exercises_raw:
        name = (ex_raw.get("name") or "").strip()
        matched = await _match_exercise(session, name)
        sets_raw = ex_raw.get("sets") or []
        sets_out: list[ParsedSet] = []
        for i, s in enumerate(sets_raw, start=1):
            sets_out.append(
                ParsedSet(
                    set_index=_int_or_none(s.get("set_index")) or i,
                    reps=_int_or_none(s.get("reps")),
                    weight_kg=_decimal_or_none(s.get("weight_kg")),
                    rpe=_decimal_or_none(s.get("rpe")),
                    is_warmup=bool(s.get("is_warmup", False)),
                )
            )
        out_exercises.append(
            ParsedExercise(matched_exercise_id=matched, name=name, sets=sets_out)
        )
    return ParsedWorkout(
        exercises=out_exercises, notes=data.get("notes"), raw=payload.text
    )


# --- Meals ---


class ParsedMealItem(BaseModel):
    name: str
    serving_g: Decimal | None = None
    kcal: Decimal | None = None
    protein_g: Decimal | None = None
    carbs_g: Decimal | None = None
    fat_g: Decimal | None = None
    confidence: Decimal | None = None


class ParsedMeal(BaseModel):
    items: list[ParsedMealItem]
    raw: str


_MEAL_PROMPT = (
    "사용자가 입력한 자유 텍스트 식단을 구조화 JSON으로 변환합니다.\n"
    "한국 식품에 대한 일반 영양정보(대략)를 기반으로 추정합니다.\n"
    "출력은 반드시 다음 스키마의 JSON 객체:\n"
    "{\n"
    '  "items": [\n'
    '    {"name": "닭가슴살", "serving_g": 200, "kcal": 330, '
    '"protein_g": 62, "carbs_g": 0, "fat_g": 7, "confidence": 0.8}\n'
    "  ]\n"
    "}\n"
    "규칙: 1) 양이 명확하지 않으면 한국 표준 1인분 기준으로 추정.\n"
    "2) confidence는 0~1 사이로 추정 신뢰도.\n"
    "3) 모르면 해당 영양소는 null."
)


@router.post("/meals/parse", response_model=ParsedMeal)
async def parse_meal(
    payload: ParseTextRequest, _user: CurrentUser, _session: SessionDep
) -> ParsedMeal:
    llm = get_llm_client()
    try:
        data = await llm.complete_json(
            [
                ChatTurn(role="system", content=_MEAL_PROMPT),
                ChatTurn(role="user", content=payload.text),
            ],
            model=get_settings().llm_parse_model,
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"LLM parse failed: {e}"
        ) from e

    items_raw = data.get("items") or []
    out: list[ParsedMealItem] = []
    for i in items_raw:
        out.append(
            ParsedMealItem(
                name=(i.get("name") or "").strip() or "unknown",
                serving_g=_decimal_or_none(i.get("serving_g")),
                kcal=_decimal_or_none(i.get("kcal")),
                protein_g=_decimal_or_none(i.get("protein_g")),
                carbs_g=_decimal_or_none(i.get("carbs_g")),
                fat_g=_decimal_or_none(i.get("fat_g")),
                confidence=_decimal_or_none(i.get("confidence")),
            )
        )
    return ParsedMeal(items=out, raw=payload.text)


# --- Audio parsers (voice input) ---


async def _read_audio(audio: UploadFile) -> tuple[bytes, str]:
    data = await audio.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty audio")
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "audio too large")
    return data, audio.content_type or "audio/m4a"


def _build_workout_from_json(
    data: dict[str, Any],
) -> tuple[list[ParsedExercise], str | None, str]:
    exercises_raw = data.get("exercises") or []
    out: list[ParsedExercise] = []
    for ex_raw in exercises_raw:
        name = (ex_raw.get("name") or "").strip()
        sets_raw = ex_raw.get("sets") or []
        sets_out: list[ParsedSet] = []
        for i, s in enumerate(sets_raw, start=1):
            sets_out.append(
                ParsedSet(
                    set_index=_int_or_none(s.get("set_index")) or i,
                    reps=_int_or_none(s.get("reps")),
                    weight_kg=_decimal_or_none(s.get("weight_kg")),
                    rpe=_decimal_or_none(s.get("rpe")),
                    is_warmup=bool(s.get("is_warmup", False)),
                )
            )
        out.append(ParsedExercise(matched_exercise_id=None, name=name, sets=sets_out))
    return out, data.get("notes"), str(data.get("transcript") or "")


@router.post("/workouts/parse-audio", response_model=ParsedWorkout)
async def parse_workout_audio(
    _user: CurrentUser,
    session: SessionDep,
    audio: UploadFile = File(..., description="audio blob"),
) -> ParsedWorkout:
    audio_bytes, mime = await _read_audio(audio)
    llm = get_llm_client()
    prompt = (
        _WORKOUT_PROMPT
        + "\n\n오디오는 한국어 음성입니다. 먼저 음성을 받아쓰기한 뒤 같은 JSON 객체의"
        ' "transcript" 필드에 한국어 받아쓰기 결과를 함께 포함하세요.'
    )
    try:
        data = await llm.complete_audio_json(
            system_prompt=prompt,
            user_prompt="이 음성에 담긴 운동 기록을 JSON으로 변환하세요.",
            audio_bytes=audio_bytes,
            audio_mime=mime,
        )
    except NotImplementedError as e:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "current LLM backend does not support audio input",
        ) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"LLM parse failed: {e}"
        ) from e

    out_exercises, notes, transcript = _build_workout_from_json(data)
    # Backfill matched_exercise_id using the same name-based lookup.
    for ex in out_exercises:
        ex.matched_exercise_id = await _match_exercise(session, ex.name)
    return ParsedWorkout(exercises=out_exercises, notes=notes, raw=transcript)


@router.post("/meals/parse-audio", response_model=ParsedMeal)
async def parse_meal_audio(
    _user: CurrentUser,
    _session: SessionDep,
    audio: UploadFile = File(..., description="audio blob"),
) -> ParsedMeal:
    audio_bytes, mime = await _read_audio(audio)
    llm = get_llm_client()
    prompt = (
        _MEAL_PROMPT
        + '\n\n오디오는 한국어 음성입니다. JSON에 "transcript" 필드를 추가해 받아쓰기'
        " 결과를 함께 포함하세요."
    )
    try:
        data = await llm.complete_audio_json(
            system_prompt=prompt,
            user_prompt="이 음성에 담긴 식단을 JSON으로 변환하세요.",
            audio_bytes=audio_bytes,
            audio_mime=mime,
        )
    except NotImplementedError as e:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED,
            "current LLM backend does not support audio input",
        ) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"LLM parse failed: {e}"
        ) from e

    transcript = str(data.get("transcript") or "")
    items_raw = data.get("items") or []
    out: list[ParsedMealItem] = []
    for i in items_raw:
        out.append(
            ParsedMealItem(
                name=(i.get("name") or "").strip() or "unknown",
                serving_g=_decimal_or_none(i.get("serving_g")),
                kcal=_decimal_or_none(i.get("kcal")),
                protein_g=_decimal_or_none(i.get("protein_g")),
                carbs_g=_decimal_or_none(i.get("carbs_g")),
                fat_g=_decimal_or_none(i.get("fat_g")),
                confidence=_decimal_or_none(i.get("confidence")),
            )
        )
    return ParsedMeal(items=out, raw=transcript)
