from __future__ import annotations

from typing import Any, Dict, Optional


class GymCategoryStrategy:
    slug = "gyms"
    voice_tone = "coach_motivational"
    vocab_allowed = ["retention", "acquisition lull", "member count", "hiit class", "trial spot"]
    vocab_taboo = ["lose 10kg in 3 days", "guaranteed abs", "shame"]

    @staticmethod
    def format_salutation(owner_name: Optional[str], biz_name: str) -> str:
        return owner_name if owner_name else biz_name

    @staticmethod
    def get_signal_weights() -> Dict[str, float]:
        return {
            "customer_lapsed_hard": 9.5,
            "seasonal_perf_dip": 9.0,
            "member_milestone": 8.0,
            "perf_spike": 7.5,
        }
