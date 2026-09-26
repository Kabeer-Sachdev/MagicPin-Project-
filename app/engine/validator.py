from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple
from app.engine.models import Decision
from app.schemas import ActionItem


def validate_action(action: ActionItem, decision: Optional[Decision] = None) -> Tuple[bool, str]:
    """
    Validates composed ActionItem against schema, URL restrictions, single CTA constraint,
    and grounded evidence matching.
    """
    if not action.body or not action.body.strip():
        return False, "Empty message body"

    words = action.body.strip().split()
    if len(words) > 80:
        return False, f"Message body too verbose ({len(words)} words, max 80 allowed)"

    if not action.conversation_id:
        return False, "Missing conversation_id"

    if not action.merchant_id:
        return False, "Missing merchant_id"

    if not action.trigger_id:
        return False, "Missing trigger_id"

    # URL Check (hard fail for WhatsApp templates)
    url_pattern = r'https?://[^\s]+'
    if re.search(url_pattern, action.body):
        return False, "Message body contains HTTP/HTTPS URL (disallowed)"

    # CTA Check (Must be exactly 1 allowed CTA type)
    allowed_ctas = {"binary_yes_no", "open_ended", "multi_choice_slot", "binary_confirm_cancel", "none"}
    if action.cta not in allowed_ctas:
        return False, f"Invalid CTA type: {action.cta}"

    # Strict Fact Grounding Check
    if decision:
        evidence = decision.primary_evidence
        ev_str = str(evidence)

        # 1. Number Grounding Check
        numbers = re.findall(r'\b\d+\b', action.body)
        for num_str in numbers:
            num = int(num_str)
            # Slot choices 1 and 2 are allowed for booking multi-choice
            if num in (1, 2):
                continue
            if num_str not in ev_str:
                return False, f"Manufactured number '{num_str}' in body not found in decision evidence"

        # 2. Offer Title Grounding Check
        active_offers = evidence.get("active_offers", [])
        if active_offers:
            for offer in active_offers:
                title = offer.get("title")
                # If offer title is mentioned in body, verify exact match
                if title and title.split("@")[0].strip().lower() in action.body.lower():
                    if title not in action.body and title.split("@")[0].strip() not in action.body:
                        return False, f"Offer title '{title}' misquoted in message body"

    return True, ""


def sanitize_body(body: str) -> str:
    """Removes prohibited URLs or extra whitespace."""
    url_pattern = r'https?://[^\s]+'
    sanitized = re.sub(url_pattern, '', body).strip()
    return sanitized
