from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from app.categories import get_category_strategy
from app.engine.evidence_selector import select_primary_evidence
from app.engine.models import Decision


@dataclass
class MessageBlueprint:
    blueprint_type: str  # "research_digest" | "customer_recall" | "perf_dip" | "perf_spike" | "curious_ask" | "expiring_offer" | "generic_fallback"
    salutation: str
    selected_evidence: Dict[str, Any]
    cta_type: str
    tone: str
    send_as: str = "vera"


def select_message_blueprint(decision: Decision) -> MessageBlueprint:
    """
    Selects the deterministic message blueprint and evidence set for a Decision.
    """
    evidence = decision.primary_evidence
    kind = decision.signal_type
    cat_slug = decision.category_strategy

    strat = get_category_strategy(cat_slug)
    owner_name = evidence.get("owner_first_name")
    merchant_name = evidence.get("merchant_name", "your business")
    salutation = strat.format_salutation(owner_name, merchant_name)
    tone = getattr(strat, "voice_tone", "warm_practical")

    selected_ev = select_primary_evidence(evidence, kind)

    # Blueprint Selection
    if kind == "research_digest":
        b_type = "research_digest"
        cta_type = "open_ended"
    elif kind in {"recall_due", "chronic_refill_due"} or decision.send_as == "merchant_on_behalf":
        b_type = "customer_recall"
        cta_type = "multi_choice_slot"
    elif kind in {"perf_dip", "seasonal_perf_dip"}:
        b_type = "perf_dip"
        cta_type = "binary_yes_no"
    elif kind in {"perf_spike", "milestone_reached"}:
        b_type = "perf_spike"
        cta_type = "binary_yes_no"
    elif kind == "curious_ask_due":
        b_type = "curious_ask"
        cta_type = "open_ended"
    elif evidence.get("days_remaining") and evidence["days_remaining"] <= 14:
        b_type = "expiring_offer"
        cta_type = "binary_yes_no"
    else:
        b_type = "generic_fallback"
        cta_type = "binary_yes_no"

    return MessageBlueprint(
        blueprint_type=b_type,
        salutation=salutation,
        selected_evidence=selected_ev,
        cta_type=cta_type,
        tone=tone,
        send_as=decision.send_as
    )
