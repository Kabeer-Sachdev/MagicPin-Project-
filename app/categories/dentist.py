from __future__ import annotations

from typing import Any, Dict, Optional


class DentistCategoryStrategy:
    slug = "dentists"
    voice_tone = "peer_clinical"
    vocab_allowed = ["fluoride varnish", "caries", "bruxism", "recall", "alignment", "high-risk adult"]
    vocab_taboo = ["cure", "guaranteed", "100% safe", "miracle"]

    @staticmethod
    def format_salutation(owner_name: Optional[str], biz_name: str) -> str:
        if owner_name:
            prefix = owner_name if owner_name.startswith("Dr.") else f"Dr. {owner_name}"
            return prefix
        return biz_name

    @staticmethod
    def get_signal_weights() -> Dict[str, float]:
        return {
            "research_digest": 9.5,
            "recall_due": 9.0,
            "ctr_below_peer": 8.0,
            "stale_posts": 7.0,
            "perf_dip": 7.5,
            "curious_ask_due": 6.0,
        }
