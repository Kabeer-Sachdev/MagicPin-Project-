from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.engine.models import Signal
from app.engine.normalizer import (
    calculate_actionability_score,
    calculate_recency_score,
    calculate_specificity_score,
    safe_pct_change,
)


def extract_normalized_signals(
    trigger: Dict[str, Any],
    merchant: Optional[Dict[str, Any]] = None,
    category: Optional[Dict[str, Any]] = None,
    customer: Optional[Dict[str, Any]] = None,
) -> List[Signal]:
    """
    Extracts normalized Signal instances from raw context JSON.
    Guarantees no manufactured values; only extracts grounded evidence.
    """
    signals: List[Signal] = []
    if not trigger:
        return signals

    trg_id = trigger.get("id", "trg_unknown")
    kind = trigger.get("kind", "generic_nudge")
    scope = trigger.get("scope", "merchant")
    source = trigger.get("source", "external")
    urgency = trigger.get("urgency", 1)
    suppression_key = trigger.get("suppression_key", f"{kind}:{trigger.get('merchant_id', '')}")
    merchant_id = trigger.get("merchant_id") or (merchant.get("merchant_id") if merchant else "unknown")
    customer_id = trigger.get("customer_id") or (customer.get("customer_id") if customer else None)

    cat_slug = category.get("slug") if category else (merchant.get("category_slug") if merchant else "")

    evidence: Dict[str, Any] = {
        "kind": kind,
        "trigger_payload": trigger.get("payload", {}),
        "category_slug": cat_slug,
    }

    value = None
    prev_val = None
    change_pct = None
    unit = None

    if merchant:
        identity = merchant.get("identity", {})
        perf = merchant.get("performance", {})
        sub = merchant.get("subscription", {})
        agg = merchant.get("customer_aggregate", {})
        offers = merchant.get("offers", [])
        active_offers = [o for o in offers if o.get("status") == "active"]

        evidence["merchant_name"] = identity.get("name")
        evidence["owner_first_name"] = identity.get("owner_first_name")
        evidence["locality"] = identity.get("locality")
        evidence["city"] = identity.get("city")
        evidence["languages"] = identity.get("languages", ["en"])
        evidence["views"] = perf.get("views")
        evidence["calls"] = perf.get("calls")
        evidence["directions"] = perf.get("directions")
        evidence["ctr"] = perf.get("ctr")
        evidence["delta_7d"] = perf.get("delta_7d", {})
        evidence["signals"] = merchant.get("signals", [])
        evidence["days_remaining"] = sub.get("days_remaining")
        evidence["sub_status"] = sub.get("status")
        evidence["total_unique_ytd"] = agg.get("total_unique_ytd")
        evidence["high_risk_adult_count"] = agg.get("high_risk_adult_count")
        evidence["active_offers"] = active_offers

        # Extract delta percentage if available
        if "views_pct" in perf.get("delta_7d", {}):
            change_pct = float(perf["delta_7d"]["views_pct"]) * 100.0
            value = perf.get("views")
            unit = "views"

    if category:
        digest = category.get("digest", [])
        evidence["peer_stats"] = category.get("peer_stats", {})
        evidence["digest"] = digest
        evidence["voice"] = category.get("voice", {})

        # If trigger is research digest, match top item
        if kind == "research_digest" and digest:
            trg_payload = trigger.get("payload", {})
            top_item_id = trg_payload.get("top_item_id")
            top_item = next((item for item in digest if item.get("id") == top_item_id), digest[0])
            evidence["top_digest_item"] = top_item
            evidence["digest_source"] = top_item.get("source")
            evidence["trial_n"] = top_item.get("trial_n")

    if customer:
        c_ident = customer.get("identity", {})
        c_rel = customer.get("relationship", {})
        c_pref = customer.get("preferences", {})
        evidence["customer_name"] = c_ident.get("name")
        evidence["customer_language"] = c_ident.get("language_pref", "en")
        evidence["visits_total"] = c_rel.get("visits_total")
        evidence["services_received"] = c_rel.get("services_received", [])
        evidence["customer_state"] = customer.get("state")
        evidence["preferred_slots"] = c_pref.get("preferred_slots")

    recency_score = calculate_recency_score(trigger.get("delivered_at"))
    specificity_score = calculate_specificity_score(evidence)
    actionability_score = calculate_actionability_score(evidence, kind)
    relevance_score = 1.0  # matched by merchant & category

    sig = Signal(
        signal_id=trg_id,
        type=kind,
        source=source,
        merchant_id=merchant_id,
        category=cat_slug,
        scope=scope,
        customer_id=customer_id,
        value=value,
        previous_value=prev_val,
        change_pct=change_pct,
        unit=unit,
        timestamp=trigger.get("delivered_at"),
        urgency=urgency,
        recency_score=recency_score,
        actionability_score=actionability_score,
        specificity_score=specificity_score,
        relevance_score=relevance_score,
        confidence=1.0,
        suppression_key=suppression_key,
        evidence=evidence,
        raw_payload=trigger
    )
    signals.append(sig)
    return signals
