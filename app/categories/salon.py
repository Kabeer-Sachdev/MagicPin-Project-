from __future__ import annotations

from typing import Any, Dict, Optional


class SalonCategoryStrategy:
    slug = "salons"
    voice_tone = "warm_practical"
    vocab_allowed = ["balayage", "haircut", "facial", "skin-prep", "bridal trial", "hair spa"]
    vocab_taboo = ["flat 50% off", "cheap", "guaranteed transformation"]

    @staticmethod
    def format_salutation(owner_name: Optional[str], biz_name: str) -> str:
        return owner_name if owner_name else biz_name

    @staticmethod
    def get_signal_weights() -> Dict[str, float]:
        return {
            "bridal_followup": 9.5,
            "curious_ask_due": 8.5,
            "perf_spike": 8.0,
            "review_theme_emerged": 7.5,
            "stale_posts": 7.0,
        }
