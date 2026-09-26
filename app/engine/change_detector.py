from __future__ import annotations

from typing import Any, Dict, Optional
from app.engine.normalizer import safe_pct_change


def detect_context_changes(current_payload: Dict[str, Any], previous_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compares current context payload vs previous version payload deterministically.
    Returns structured change report.
    """
    if not previous_payload:
        return {
            "has_changed": True,
            "is_initial": True,
            "views_delta": None,
            "pct_change": None,
            "material_change": False,
            "changes": ["initial_ingestion"]
        }

    changes = []
    material_change = False

    # 1. Performance Views Delta Check
    cur_perf = current_payload.get("performance", {})
    prev_perf = previous_payload.get("performance", {})

    cur_views = cur_perf.get("views")
    prev_views = prev_perf.get("views")

    views_delta = None
    pct_change = None

    if cur_views is not None and prev_views is not None:
        views_delta = cur_views - prev_views
        if views_delta != 0:
            pct_change = safe_pct_change(cur_views, prev_views)
            changes.append(f"views_changed:{prev_views}->{cur_views}")
            # Material change threshold: >15% view shift or >100 views absolute delta
            if (pct_change is not None and abs(pct_change) >= 15.0) or abs(views_delta) >= 100:
                material_change = True

    # 2. Offers Change Check
    cur_offers = [o.get("id") for o in current_payload.get("offers", []) if o.get("status") == "active"]
    prev_offers = [o.get("id") for o in previous_payload.get("offers", []) if o.get("status") == "active"]

    if set(cur_offers) != set(prev_offers):
        changes.append("active_offers_changed")
        material_change = True

    # 3. Digest Change Check
    cur_digest = [d.get("id") for d in current_payload.get("digest", [])]
    prev_digest = [d.get("id") for d in previous_payload.get("digest", [])]

    if set(cur_digest) != set(prev_digest):
        changes.append("digest_items_updated")
        material_change = True

    has_changed = len(changes) > 0

    return {
        "has_changed": has_changed,
        "is_initial": False,
        "views_delta": views_delta,
        "pct_change": pct_change,
        "material_change": material_change,
        "changes": changes
    }
