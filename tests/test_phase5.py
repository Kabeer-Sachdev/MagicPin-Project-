from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.engine.change_detector import detect_context_changes
from app.engine.strategy import process_reply_turn, classify_inbound_intent
from app.engine.suppression import is_signal_suppressed, register_suppression
from app.main import app
from app.state import store

client = TestClient(app)
DATASET_DIR = Path(__file__).parent.parent / "dataset"


def setup_function():
    store.contexts.clear()
    store.suppressions.clear()
    store.conversations.clear()


def test_scenario_1_initial_context_to_opportunity():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m001 = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"][0]
    trg001 = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"][0]

    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": m001["merchant_id"], "version": 1, "payload": m001, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": trg001["id"], "version": 1, "payload": trg001, "delivered_at": "2026-04-26T10:00:00Z"})

    res = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": [trg001["id"]]})
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert len(actions) == 1
    assert actions[0]["merchant_id"] == m001["merchant_id"]


def test_scenario_2_same_tick_repeated_no_duplicate():
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))
    m001 = json.load(open(DATASET_DIR / "merchants_seed.json"))["merchants"][0]
    trg001 = json.load(open(DATASET_DIR / "triggers_seed.json"))["triggers"][0]

    client.post("/v1/context", json={"scope": "category", "context_id": "dentists", "version": 1, "payload": cat_payload, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "merchant", "context_id": m001["merchant_id"], "version": 1, "payload": m001, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "trigger", "context_id": trg001["id"], "version": 1, "payload": trg001, "delivered_at": "2026-04-26T10:00:00Z"})

    res1 = client.post("/v1/tick", json={"now": "2026-04-26T10:35:00Z", "available_triggers": [trg001["id"]]})
    assert len(res1.json()["actions"]) == 1

    # Repeat tick with same trigger -> Action suppressed (no duplicates)
    res2 = client.post("/v1/tick", json={"now": "2026-04-26T10:40:00Z", "available_triggers": [trg001["id"]]})
    assert len(res2.json()["actions"]) == 0


def test_scenario_3_material_change_override():
    m_v1 = {"merchant_id": "m1", "performance": {"views": 190}, "offers": []}
    m_v2 = {"merchant_id": "m1", "performance": {"views": 310}, "offers": [{"id": "o1", "status": "active"}]}

    report = detect_context_changes(m_v2, m_v1)
    assert report["has_changed"] is True
    assert report["material_change"] is True

    # Register suppression for m1
    key = "m1:perf_dip"
    register_suppression(key)

    # Without material change -> suppressed
    assert is_signal_suppressed(key, material_change=False) is True

    # With material change -> suppression lifted!
    assert is_signal_suppressed(key, material_change=True) is False


def test_scenario_4_merchant_accept():
    conv_state = {"turns": [], "consecutive_auto_replies": 0, "status": "AWAITING_RESPONSE"}
    action, body, cta, wait, rat = process_reply_turn(
        conv_id="c1", merchant_id="m1", customer_id=None, from_role="merchant",
        message="Ok, let's do it", turn_number=2, conv_state=conv_state
    )

    assert action == "send"
    assert conv_state["status"] == "ACCEPTED"
    assert cta == "binary_confirm_cancel"
    assert "Drafting your execution action" in body


def test_scenario_5_merchant_reject():
    conv_state = {"turns": [], "consecutive_auto_replies": 0, "status": "AWAITING_RESPONSE"}
    action, body, cta, wait, rat = process_reply_turn(
        conv_id="c1", merchant_id="m1", customer_id=None, from_role="merchant",
        message="Stop messaging me. Not interested.", turn_number=2, conv_state=conv_state
    )

    assert action == "end"
    assert conv_state["status"] == "REJECTED"
    assert is_signal_suppressed("opt_out:m1") is True


def test_scenario_6_merchant_clarification():
    conv_state = {"turns": [], "consecutive_auto_replies": 0, "status": "AWAITING_RESPONSE"}
    action, body, cta, wait, rat = process_reply_turn(
        conv_id="c1", merchant_id="m1", customer_id=None, from_role="merchant",
        message="Why?", turn_number=2, conv_state=conv_state
    )

    assert action == "send"
    assert conv_state["status"] == "CLARIFICATION_REQUESTED"
    assert "recent performance" in body


def test_scenario_8_off_topic_reply():
    conv_state = {"turns": [], "consecutive_auto_replies": 0, "status": "AWAITING_RESPONSE"}
    action, body, cta, wait, rat = process_reply_turn(
        conv_id="c1", merchant_id="m1", customer_id=None, from_role="merchant",
        message="Can you help me file my GST?", turn_number=2, conv_state=conv_state
    )

    assert action == "send"
    assert "GST" in body
    assert "CA" in body


def test_scenario_10_and_11_customer_and_merchant_isolation():
    c_a = {"customer_id": "c_a", "merchant_id": "m1", "identity": {"name": "Priya"}}
    c_b = {"customer_id": "c_b", "merchant_id": "m2", "identity": {"name": "Rohit"}}

    client.post("/v1/context", json={"scope": "customer", "context_id": "c_a", "version": 1, "payload": c_a, "delivered_at": "2026-04-26T10:00:00Z"})
    client.post("/v1/context", json={"scope": "customer", "context_id": "c_b", "version": 1, "payload": c_b, "delivered_at": "2026-04-26T10:00:00Z"})

    fetched_a = store.get_context("customer", "c_a")
    fetched_b = store.get_context("customer", "c_b")

    assert fetched_a["identity"]["name"] == "Priya"
    assert fetched_b["identity"]["name"] == "Rohit"
    assert fetched_a["merchant_id"] != fetched_b["merchant_id"]


def test_scenario_12_bounded_history():
    conv_id = "c_bounded"
    for i in range(25):
        store.add_turn(conv_id, "merchant", f"Turn message {i}")

    conv = store.get_conversation(conv_id)
    assert len(conv["turns"]) == 20  # Max 20 turns preserved
    assert conv["turns"][-1]["message"] == "Turn message 24"


def test_scenario_14_empty_initial_state():
    assert store.get_uptime_seconds() >= 0
    assert store.get_contexts_loaded()["category"] == 0
    assert store.get_conversation("non_existent") is None


def test_scenario_15_adversarial_nulls_and_missing_fields():
    report = detect_context_changes({"performance": None}, None)
    assert report["has_changed"] is True
    assert report["material_change"] is False

    intent = classify_inbound_intent("")
    assert intent == "engaged_general"
