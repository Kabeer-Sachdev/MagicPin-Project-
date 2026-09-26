from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Response, status
from app.schemas import ContextPushRequest, ContextPushResponse
from app.state import store

router = APIRouter()

VALID_SCOPES = {"category", "merchant", "customer", "trigger"}


@router.post("/v1/context", response_model=ContextPushResponse)
async def push_context(body: ContextPushRequest, response: Response):
    if body.scope not in VALID_SCOPES:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ContextPushResponse(
            accepted=False,
            reason="invalid_scope",
            details=f"Scope '{body.scope}' is not one of {sorted(VALID_SCOPES)}"
        )

    accepted, reason, cur_ver = store.push_context(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload,
        delivered_at=body.delivered_at
    )

    if not accepted:
        response.status_code = status.HTTP_409_CONFLICT
        return ContextPushResponse(
            accepted=False,
            reason=reason,
            current_version=cur_ver
        )

    return ContextPushResponse(
        accepted=True,
        ack_id=f"ack_{body.context_id}_v{body.version}",
        stored_at=datetime.utcnow().isoformat() + "Z"
    )
