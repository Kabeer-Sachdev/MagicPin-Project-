from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.engine.models import Decision, Signal
from app.engine.normalizer import safe_pct_change, calculate_recency_score, calculate_specificity_score
from app.engine.signals import extract_normalized_signals
from app.engine.ranking import deduplicate_signals, select_best_decision, score_opportunity
from app.engine.composer import compose_message_from_decision
from app.engine.validator import validate_action
from app.main import app
from app.schemas import ActionItem
from app.state import store

client = TestClient(app)
DATASET_DIR = Path(__file__).parent.parent / "dataset"


def setup_function():
    store.contexts.clear()
    store.suppressions.clear()
    store.conversations.clear()


def test_normalizer_safe_pct_change():
    assert safe_pct_change(190, 140) == 35.71
    assert safe_pct_change(80, 100) == -20.0
    assert safe_pct_change(100, 0) == 100.0
    assert safe_pct_change(None, 100) is None
    assert safe_pct_change(100, None) is None


def test_signal_extraction_and_scoring():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    merchants_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"]
    triggers_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"]

    m001 = merchants_payload[0]
    trg001 = triggers_payload[0]

    signals = extract_normalized_signals(trigger=trg001, merchant=m001, category=cat_payload)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.merchant_id == m001["merchant_id"]
    assert sig.category == "dentists"
    assert sig.urgency == trg001["urgency"]


def test_deduplication_and_decision_selection():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    merchants_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"]
    triggers_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"]

    m001 = merchants_payload[0]
    trg001 = triggers_payload[0]

    signals = extract_normalized_signals(trigger=trg001, merchant=m001, category=cat_payload)
    decision = select_best_decision(signals)

    assert decision is not None
    assert isinstance(decision, Decision)
    assert decision.merchant_id == m001["merchant_id"]
    assert decision.signal_type == trg001["kind"]
    assert decision.score > 0
    assert "Selected 'research_digest'" in decision.rationale


def test_composer_grounded_in_decision():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    merchants_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"]
    triggers_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"]

    m001 = merchants_payload[0]
    trg001 = triggers_payload[0]

    signals = extract_normalized_signals(trigger=trg001, merchant=m001, category=cat_payload)
    decision = select_best_decision(signals)
    assert decision is not None

    action = compose_message_from_decision(decision)
    assert isinstance(action, ActionItem)
    assert "Dr. Meera" in action.body
    assert action.cta in {"open_ended", "binary_yes_no", "multi_choice_slot", "binary_confirm_cancel"}

    is_valid, err = validate_action(action, decision)
    assert is_valid is True, err


def test_suppression_blocks_decision():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    merchants_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"]
    triggers_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"]

    m001 = merchants_payload[0]
    trg001 = triggers_payload[0]

    signals = extract_normalized_signals(trigger=trg001, merchant=m001, category=cat_payload)
    key = signals[0].suppression_key

    # Suppress key in store
    store.add_suppression(key)

    decision = select_best_decision(signals)
    assert decision is None  # Suppressed signal must be skipped


def test_full_pipeline_via_tick_api():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    merchants_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"]
    triggers_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"]

    m001 = merchants_payload[0]
    trg001 = triggers_payload[0]

    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": m001["merchant_id"], "version": 1, "payload": m001, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": trg001["id"], "version": 1, "payload": trg001, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": [trg001["id"]]})
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["merchant_id"] == m001["merchant_id"]
    assert "JIDA" in actions[0]["body"] or "Dr. Meera" in actions[0]["body"]
