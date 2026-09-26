from __future__ import annotations

import logging
from fastapi import APIRouter
from app.engine.change_detector import detect_context_changes
from app.engine.composer import compose_message_from_decision
from app.engine.ranking import select_best_decision
from app.engine.signals import extract_normalized_signals
from app.engine.suppression import register_suppression, is_signal_suppressed
from app.engine.validator import validate_action
from app.schemas import TickRequest, TickResponse
from app.state import store

logger = logging.getLogger("vera.routes.tick")
router = APIRouter()


@router.post("/v1/tick", response_model=TickResponse)
async def handle_tick(body: TickRequest):
    actions = []
    processed_merchants = set()

    for trg_id in body.available_triggers:
        trg_payload = store.get_context("trigger", trg_id)
        if not trg_payload:
            continue

        merchant_id = trg_payload.get("merchant_id")
        if merchant_id in processed_merchants:
            continue  # Max 1 action per merchant per tick

        merchant_entry = store.get_context_entry("merchant", merchant_id) if merchant_id else None
        merchant_payload = merchant_entry["payload"] if merchant_entry else None
        prev_merchant_payload = merchant_entry.get("previous_payload") if merchant_entry else None

        # Detect context changes & material change flag
        change_report = detect_context_changes(merchant_payload or {}, prev_merchant_payload)
        material_change = change_report.get("material_change", False)

        cat_slug = merchant_payload.get("category_slug") if merchant_payload else trg_payload.get("payload", {}).get("category")
        category_payload = store.get_context("category", cat_slug) if cat_slug else None

        customer_id = trg_payload.get("customer_id")
        customer_payload = store.get_context("customer", customer_id) if customer_id else None

        # 1. Extract Normalized Signals
        extracted_signals = extract_normalized_signals(
            trigger=trg_payload,
            merchant=merchant_payload,
            category=category_payload,
            customer=customer_payload
        )

        # 2. Score, Deduplicate & Select Primary Decision
        decision = select_best_decision(extracted_signals)
        if not decision:
            continue

        # Check suppression with material change override
        if is_signal_suppressed(decision.suppression_key, material_change=material_change):
            continue

        # 3. Compose Action Item from Decision
        action = compose_message_from_decision(decision)

        # 4. Validate Action & Grounding
        is_valid, err_reason = validate_action(action, decision)
        if not is_valid:
            logger.warning(f"Action validation failed for trigger {trg_id}: {err_reason}")
            continue

        # 5. Register Suppression Key & Update Conversation State
        register_suppression(action.suppression_key, reason="tick_action_sent")
        if merchant_id:
            processed_merchants.add(merchant_id)

        conv_state = store.get_conversation(action.conversation_id) or store.update_conversation(action.conversation_id, {})
        conv_state["status"] = "MESSAGE_SENT"
        conv_state["last_action"] = "send"
        conv_state["suppression_key"] = action.suppression_key

        actions.append(action)
        if len(actions) >= 20:  # Cap at 20 actions per tick
            break

    return TickResponse(actions=actions)
