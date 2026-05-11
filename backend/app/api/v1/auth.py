from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from jose import JWTError
from sqlalchemy import select

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.deps import CurrentUser, SessionDep
from app.models.profile import Profile
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep) -> TokenPair:
    email = payload.email.lower()
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    user = User(email=email, password_hash=hash_password(payload.password))
    user.profile = Profile()
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginRequest, session: SessionDep) -> TokenPair:
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(user.password_hash, payload.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, session: SessionDep) -> TokenPair:
    try:
        user_id = decode_token(payload.refresh_token, "refresh")
    except JWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid refresh token: {e}") from e
    user = await session.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(id=str(user.id), email=user.email)
