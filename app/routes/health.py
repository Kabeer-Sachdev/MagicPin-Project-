from __future__ import annotations

from fastapi import APIRouter
from app.schemas import HealthzResponse
from app.state import store

router = APIRouter()


@router.get("/v1/healthz", response_model=HealthzResponse)
async def get_healthz():
    return HealthzResponse(
        status="ok",
        uptime_seconds=store.get_uptime_seconds(),
        contexts_loaded=store.get_contexts_loaded()
    )
