from __future__ import annotations

from typing import Any, Dict, Optional


class PharmacyCategoryStrategy:
    slug = "pharmacies"
    voice_tone = "trustworthy_precise"
    vocab_allowed = ["chronic-rx", "dosage", "recall alert", "sub-potency", "refill", "home delivery"]
    vocab_taboo = ["cure all", "100% cure", "cheap drugs"]

    @staticmethod
    def format_salutation(owner_name: Optional[str], biz_name: str) -> str:
        return owner_name if owner_name else biz_name

    @staticmethod
    def get_signal_weights() -> Dict[str, float]:
        return {
            "supply_alert": 10.0,
            "chronic_refill_due": 9.5,
            "recall_alert": 9.5,
            "perf_dip": 7.0,
        }
