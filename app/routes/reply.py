from __future__ import annotations

from fastapi import APIRouter
from app.engine.strategy import process_reply_turn
from app.schemas import ReplyRequest, ReplyResponse
from app.state import store

router = APIRouter()


@router.post("/v1/reply", response_model=ReplyResponse)
async def handle_reply(body: ReplyRequest):
    # Store turn history
    store.add_turn(
        conversation_id=body.conversation_id,
        role=body.from_role,
        message=body.message,
        ts=body.received_at
    )

    conv_state = store.get_conversation(body.conversation_id)

    action, resp_body, cta, wait_seconds, rationale = process_reply_turn(
        conv_id=body.conversation_id,
        merchant_id=body.merchant_id,
        customer_id=body.customer_id,
        from_role=body.from_role,
        message=body.message,
        turn_number=body.turn_number,
        conv_state=conv_state
    )

    # Store last action
    conv_state["last_action"] = action

    return ReplyResponse(
        action=action,
        body=resp_body,
        cta=cta,
        wait_seconds=wait_seconds,
        rationale=rationale
    )
