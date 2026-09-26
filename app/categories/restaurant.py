from __future__ import annotations

from typing import Any, Dict, Optional


class RestaurantCategoryStrategy:
    slug = "restaurants"
    voice_tone = "operator_to_operator"
    vocab_allowed = ["covers", "delivery radius", "ipl match", "bogo", "thali", "order volume"]
    vocab_taboo = ["best food in city", "guaranteed taste"]

    @staticmethod
    def format_salutation(owner_name: Optional[str], biz_name: str) -> str:
        return owner_name if owner_name else biz_name

    @staticmethod
    def get_signal_weights() -> Dict[str, float]:
        return {
            "ipl_match_today": 9.5,
            "active_planning_intent": 9.0,
            "weather_heatwave": 8.5,
            "festival_upcoming": 8.0,
            "perf_dip": 7.5,
        }
