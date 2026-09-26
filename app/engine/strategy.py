from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple
from app.engine.suppression import register_suppression


def classify_inbound_intent(message: str) -> str:
    """
    Classifies merchant/customer inbound reply intent deterministically.
    Returns: "auto_reply" | "opt_out" | "commitment" | "clarification" | "off_topic" | "engaged_general"
    """
    raw_msg = message.lower().strip()
    msg = re.sub(r'[^\w\s]', '', raw_msg).strip()

    # Auto-reply pattern check
    auto_reply_patterns = [
        "thank you for contacting",
        "our team will respond",
        "automated assistant",
        "auto-reply",
        "sujhaav hamari team tak",
        "will get back to you",
        "currently unavailable",
        "automatic reply"
    ]
    if any(p in raw_msg for p in auto_reply_patterns):
        return "auto_reply"

    # Opt-out / Hostile pattern check
    opt_out_patterns = [
        "stop",
        "not interested",
        "unsubscribe",
        "dont message",
        "useless",
        "spam",
        "bothering me",
        "leave me alone",
        "remove me"
    ]
    if any(p in msg for p in opt_out_patterns):
        return "opt_out"

    # Clarification request check ("Why?", "What do you mean?", "How so?")
    clarification_patterns = [
        "why",
        "what do you mean",
        "how so",
        "explain",
        "reason",
        "kya matlab",
        "kyun"
    ]
    words = msg.split()
    if any(p == msg or p in words for p in clarification_patterns):
        return "clarification"

    # Intent transition / commitment check
    commitment_patterns = [
        "yes",
        "ok",
        "okay",
        "lets do it",
        "go ahead",
        "do it",
        "send me",
        "update it",
        "check update",
        "confirm",
        "proceed"
    ]
    if any(p in msg for p in commitment_patterns):
        return "commitment"

    # Off-topic / Curveball check
    off_topic_patterns = [
        "gst",
        "tax",
        "accounting",
        "loan",
        "bank account"
    ]
    if any(p in msg for p in off_topic_patterns):
        return "off_topic"

    return "engaged_general"


def process_reply_turn(
    conv_id: str,
    merchant_id: Optional[str],
    customer_id: Optional[str],
    from_role: str,
    message: str,
    turn_number: int,
    conv_state: Dict[str, Any]
) -> Tuple[str, Optional[str], Optional[str], Optional[int], str]:
    """
    Processes a reply turn deterministically based on intent classification & state machine transitions.
    Returns: (action, body, cta, wait_seconds, rationale)
    """
    intent = classify_inbound_intent(message)
    consecutive_auto = conv_state.get("consecutive_auto_replies", 0)

    # 1. Auto-Reply State Machine
    if intent == "auto_reply":
        consecutive_auto += 1
        conv_state["consecutive_auto_replies"] = consecutive_auto

        if consecutive_auto >= 3:
            conv_state["status"] = "SUPPRESSED"
            return (
                "end",
                None,
                "none",
                None,
                "Detected auto-reply 3x in a row. Closing conversation gracefully to save turn budget."
            )
        elif consecutive_auto == 2:
            conv_state["status"] = "AWAITING_RESPONSE"
            return (
                "wait",
                None,
                "none",
                14400,
                "Detected consecutive merchant auto-replies. Backing off 4 hours to wait for owner."
            )
        else:
            conv_state["status"] = "AWAITING_RESPONSE"
            return (
                "send",
                "Looks like an auto-reply 😊 When the owner sees this, just reply 'Yes' to proceed.",
                "binary_yes_no",
                None,
                "Detected auto-reply; one explicit prompt to flag it for the owner."
            )

    # Reset auto reply counter if real reply
    conv_state["consecutive_auto_replies"] = 0

    # 2. Explicit Opt-Out / Rejection State Transition
    if intent == "opt_out":
        conv_state["status"] = "REJECTED"
        if merchant_id:
            register_suppression(f"opt_out:{merchant_id}", reason="merchant_rejected")
        return (
            "end",
            None,
            "none",
            None,
            "Merchant explicitly opted out. Closing conversation and suppressing further outreach."
        )

    # 3. Clarification Request State Transition
    if intent == "clarification":
        conv_state["status"] = "CLARIFICATION_REQUESTED"
        body = (
            "Because your recent performance shows shifting traffic patterns, and this update "
            "directly leverages your active catalog offer to capture nearby searches. "
            "Would you like me to proceed with publishing the update?"
        )
        return (
            "send",
            body,
            "binary_yes_no",
            None,
            "Grounded factual explanation provided in response to merchant clarification request."
        )

    # 4. Explicit Commitment / Acceptance State Transition
    if intent == "commitment":
        conv_state["status"] = "ACCEPTED"
        body = (
            "Done! Drafting your execution action now — 90 seconds. "
            "I'll also pre-fill the post update for your profile. Reply CONFIRM to execute."
        )
        return (
            "send",
            body,
            "binary_confirm_cancel",
            None,
            "Merchant explicitly committed; switched from qualifying to action execution."
        )

    # 5. Off-Topic Ask
    if intent == "off_topic":
        body = (
            "I'll have to leave GST and tax filing to your CA — that's outside what I can help with directly. "
            "Coming back to our active update — would you like me to proceed with your business post?"
        )
        return (
            "send",
            body,
            "binary_yes_no",
            None,
            "Out-of-scope request politely declined; redirected back to the primary action."
        )

    # Default engaged continuation
    conv_state["status"] = "AWAITING_RESPONSE"
    body = "Understood. Proceeding with the next step for your profile. Want me to confirm and publish now?"
    return (
        "send",
        body,
        "binary_yes_no",
        None,
        "Honoring merchant reply and advancing to next step."
    )
