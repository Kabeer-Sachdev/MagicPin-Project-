from __future__ import annotations

import json
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.engine.composer import compose_message_from_decision
from app.engine.ranking import select_best_decision
from app.engine.signals import extract_normalized_signals
from app.engine.strategy import process_reply_turn
from app.engine.suppression import is_signal_suppressed, register_suppression
from app.engine.validator import validate_action
from app.main import app
from app.state import store

client = TestClient(app)
DATASET_DIR = Path(__file__).parent.parent / "dataset"


def setup_function():
    store.contexts.clear()
    store.suppressions.clear()
    store.conversations.clear()


def test_expiring_offer_beats_stale_demand():
    """Verify high-urgency offer renewal/expiring signal outranks low-urgency demand signal."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m_payload = {
        "merchant_id": "m_renew",
        "category_slug": "dentists",
        "identity": {"name": "Renew Dental", "owner_first_name": "Meera"},
        "subscription": {"status": "active", "days_remaining": 5},
        "performance": {"views": 1000},
        "offers": []
    }

    trg_demand = {"id": "t1", "kind": "curious_ask_due", "scope": "merchant", "merchant_id": "m_renew", "urgency": 1, "suppression_key": "k1"}
    trg_renewal = {"id": "t2", "kind": "renewal_due", "scope": "merchant", "merchant_id": "m_renew", "urgency": 4, "suppression_key": "k2"}

    sig1 = extract_normalized_signals(trg_demand, m_payload, cat_payload)[0]
    sig2 = extract_normalized_signals(trg_renewal, m_payload, cat_payload)[0]

    # Select best decision from both signals
    decision = select_best_decision([sig1, sig2])
    assert decision is not None
    assert decision.signal_type == "renewal_due"


def test_rejected_opportunity_is_suppressed():
    """Verify that merchant rejection registers suppression and closes conversation."""
    conv_state = {"turns": [], "consecutive_auto_replies": 0, "status": "AWAITING_RESPONSE"}
    action, body, cta, wait, rat = process_reply_turn(
        conv_id="c_reject", merchant_id="m_reject", customer_id=None, from_role="merchant",
        message="Stop messaging me. Not interested.", turn_number=1, conv_state=conv_state
    )

    assert action == "end"
    assert is_signal_suppressed("opt_out:m_reject") is True


def test_new_offer_breaks_old_suppression():
    """Verify that a material context change (e.g. new offer) lifts stale suppression."""
    key = "m_suppress:perf_dip"
    register_suppression(key, reason="stale_tick")

    # Suppression active
    assert is_signal_suppressed(key, material_change=False) is True

    # Material change occurs -> suppression lifted
    assert is_signal_suppressed(key, material_change=True) is False


def test_missing_price_is_not_invented():
    """Verify that missing price/offers result in zero invented price figures in body."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m_no_price = {
        "merchant_id": "m_noprice",
        "category_slug": "dentists",
        "identity": {"name": "No Price Dental"},
        "offers": []
    }
    trg = {"id": "t_noprice", "kind": "perf_dip", "scope": "merchant", "merchant_id": "m_noprice", "urgency": 2, "suppression_key": "knp"}

    signals = extract_normalized_signals(trg, m_no_price, cat_payload)
    decision = select_best_decision(signals)
    assert decision is not None

    action = compose_message_from_decision(decision)
    is_valid, err = validate_action(action, decision)
    assert is_valid is True, err
    assert "₹" not in action.body  # Must NOT manufacture ₹ price figure


def test_merchant_state_is_isolated():
    """Verify strict state isolation between two merchants in the same category."""
    m_a = {"merchant_id": "m_a", "identity": {"name": "Clinic A"}, "offers": [{"title": "Offer A @ ₹299", "status": "active"}]}
    m_b = {"merchant_id": "m_b", "identity": {"name": "Clinic B"}, "offers": [{"title": "Offer B @ ₹499", "status": "active"}]}

    store.push_context("merchant", "m_a", 1, m_a, "2026-04-26T10:00:00Z")
    store.push_context("merchant", "m_b", 1, m_b, "2026-04-26T10:00:00Z")

    ret_a = store.get_context("merchant", "m_a")
    ret_b = store.get_context("merchant", "m_b")

    assert ret_a["offers"][0]["title"] == "Offer A @ ₹299"
    assert ret_b["offers"][0]["title"] == "Offer B @ ₹499"
    assert ret_a["identity"]["name"] != ret_b["identity"]["name"]


def test_determinism_across_runs():
    """Verify identical input + state produces identical decision and body across 5 executions."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"][0]
    trg_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"][0]

    bodies = []
    for _ in range(5):
        signals = extract_normalized_signals(trg_payload, m_payload, cat_payload)
        decision = select_best_decision(signals)
        action = compose_message_from_decision(decision)
        bodies.append(action.body)

    assert len(set(bodies)) == 1  # 100% deterministic, zero variance


def test_performance_within_latency_budget():
    """Verify processing latency is well within 50ms (budget is 30,000ms)."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m_payload = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"][0]
    trg_payload = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"][0]

    start = time.time()
    for _ in range(20):
        signals = extract_normalized_signals(trg_payload, m_payload, cat_payload)
        decision = select_best_decision(signals)
        compose_message_from_decision(decision)
    elapsed_ms = (time.time() - start) * 1000

    avg_ms = elapsed_ms / 20.0
    assert avg_ms < 50.0  # Must complete under 50ms per iteration
