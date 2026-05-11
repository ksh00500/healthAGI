from fastapi import APIRouter

from app.api.v1 import auth, health, muscle_groups, profile, timers

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(timers.router)
api_router.include_router(muscle_groups.router)
api_router.include_router(health.router)
