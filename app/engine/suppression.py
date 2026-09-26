from __future__ import annotations

from typing import Any, Dict, Optional
from app.state import store


def build_granular_suppression_key(merchant_id: str, signal_type: str, context_id: str = "", customer_id: Optional[str] = None) -> str:
    """
    Builds a granular, unambiguous suppression key.
    Format: merchant_id:signal_type[:context_id][:customer_id]
    """
    key = f"{merchant_id}:{signal_type}"
    if context_id:
        key += f":{context_id}"
    if customer_id:
        key += f":{customer_id}"
    return key


def is_signal_suppressed(suppression_key: str, material_change: bool = False) -> bool:
    """
    Checks if a suppression key is active.
    If material_change is True, overrides and lifts stale suppression!
    """
    if not suppression_key:
        return False

    if store.is_suppressed(suppression_key):
        if material_change:
            # Lift stale suppression due to material context change
            store.remove_suppression(suppression_key)
            return False
        return True

    return False


def register_suppression(suppression_key: str, reason: str = "handled", expires_at: Optional[str] = None):
    if suppression_key:
        store.add_suppression(suppression_key, reason=reason, expires_at=expires_at)
