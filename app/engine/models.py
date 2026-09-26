from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Signal:
    signal_id: str
    type: str
    source: str  # "external" | "internal" | "trigger"
    merchant_id: str
    category: str
    scope: str = "merchant"  # "merchant" | "customer"
    customer_id: Optional[str] = None
    value: Optional[Any] = None
    previous_value: Optional[Any] = None
    change_pct: Optional[float] = None
    unit: Optional[str] = None
    timestamp: Optional[str] = None
    urgency: int = 1
    recency_score: float = 1.0
    actionability_score: float = 1.0
    specificity_score: float = 1.0
    relevance_score: float = 1.0
    confidence: float = 1.0
    suppression_key: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    raw_payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Opportunity:
    opportunity_id: str
    merchant_id: str
    primary_signal: Signal
    supporting_signals: List[Signal] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""
    score: float = 0.0
    suppression_key: str = ""


@dataclass
class Decision:
    opportunity_id: str
    merchant_id: str
    customer_id: Optional[str]
    signal_type: str
    score: float
    primary_evidence: Dict[str, Any]
    supporting_evidence: List[Dict[str, Any]]
    recommended_action: str
    category_strategy: str
    suppression_key: str
    rationale: str
    send_as: str = "vera"
    trigger_id: str = ""
