from __future__ import annotations

from typing import Dict

# Transparent, configurable scoring weights for signal ranking
SCORING_WEIGHTS: Dict[str, float] = {
    "base_trigger_strength": 10.0,
    "magnitude": 5.0,
    "recency": 4.0,
    "merchant_relevance": 5.0,
    "actionability": 6.0,
    "specificity": 5.0,
    "category_fit": 5.0,
    "customer_relevance": 6.0,
    "repetition_penalty": 7.0,
    "suppression_penalty": 20.0
}


def get_weight(factor: str, default: float = 1.0) -> float:
    return SCORING_WEIGHTS.get(factor, default)
