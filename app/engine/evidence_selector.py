from __future__ import annotations

from typing import Any, Dict, List, Optional


def select_primary_evidence(evidence: Dict[str, Any], kind: str) -> Dict[str, Any]:
    """
    Selects the minimum, strongest set of 1-3 grounded facts from primary evidence
    to make the composed message specific and compelling without fact overloading.
    """
    selected: Dict[str, Any] = {
        "merchant_name": evidence.get("merchant_name"),
        "owner_first_name": evidence.get("owner_first_name"),
        "locality": evidence.get("locality"),
        "category_slug": evidence.get("category_slug"),
    }

    # 1. Digest/Research specific evidence
    if kind == "research_digest":
        top_item = evidence.get("top_digest_item")
        if not top_item and evidence.get("digest"):
            top_item = evidence["digest"][0]
        if top_item:
            selected["title"] = top_item.get("title")
            selected["source"] = top_item.get("source")
            selected["trial_n"] = top_item.get("trial_n")

    # 2. Recall / Customer specific evidence
    elif kind in {"recall_due", "chronic_refill_due"} or evidence.get("customer_name"):
        selected["customer_name"] = evidence.get("customer_name")
        selected["customer_language"] = evidence.get("customer_language")
        selected["preferred_slots"] = evidence.get("preferred_slots")
        active_offers = evidence.get("active_offers", [])
        if active_offers:
            selected["offer_title"] = active_offers[0].get("title")

    # 3. Performance metric deltas & counts
    elif kind in {"perf_dip", "seasonal_perf_dip", "perf_spike", "milestone_reached"}:
        selected["views"] = evidence.get("views")
        selected["calls"] = evidence.get("calls")
        delta_7d = evidence.get("delta_7d", {})
        if "views_pct" in delta_7d:
            selected["views_pct"] = round(float(delta_7d["views_pct"]) * 100.0, 1)

    # 4. Active Offers
    active_offers = evidence.get("active_offers", [])
    if active_offers and "offer_title" not in selected:
        selected["offer_title"] = active_offers[0].get("title")

    return selected
