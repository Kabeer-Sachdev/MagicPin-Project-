from __future__ import annotations

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.engine.composer import compose_message_from_decision
from app.engine.models import Decision
from app.engine.ranking import select_best_decision
from app.engine.signals import extract_normalized_signals
from app.engine.strategy_selector import select_message_blueprint
from app.engine.validator import validate_action
from app.main import app
from app.state import store

client = TestClient(app)
DATASET_DIR = Path(__file__).parent.parent / "dataset"


def setup_function():
    store.contexts.clear()
    store.suppressions.clear()
    store.conversations.clear()


def test_category_matrix_all_5_verticals():
    categories = ["dentists", "salons", "restaurants", "gyms", "pharmacies"]

    for cat_slug in categories:
        cat_file = DATASET_DIR / "categories" / f"{cat_slug}.json"
        assert cat_file.exists(), f"Missing dataset file for category {cat_slug}"
        cat_payload = json.load(open(cat_file))

        trg_payload = {
            "id": f"trg_test_{cat_slug}",
            "kind": "curious_ask_due" if cat_slug == "salons" else "perf_dip",
            "scope": "merchant",
            "source": "internal",
            "merchant_id": f"m_test_{cat_slug}",
            "payload": {"category": cat_slug},
            "urgency": 3,
            "suppression_key": f"test:{cat_slug}"
        }

        m_payload = {
            "merchant_id": f"m_test_{cat_slug}",
            "category_slug": cat_slug,
            "identity": {"name": f"Test {cat_slug.capitalize()} Biz", "owner_first_name": "Alex", "locality": "TestLoc"},
            "subscription": {"status": "active", "days_remaining": 30},
            "performance": {"window_days": 30, "views": 1500, "calls": 20, "ctr": 0.03},
            "offers": [{"id": "o1", "title": "Service Special @ ₹199", "status": "active"}],
            "signals": []
        }

        signals = extract_normalized_signals(trigger=trg_payload, merchant=m_payload, category=cat_payload)
        decision = select_best_decision(signals)
        assert decision is not None

        action = compose_message_from_decision(decision)
        assert action.merchant_id == f"m_test_{cat_slug}"
        assert len(action.body.split()) <= 80
        assert "http://" not in action.body
        assert "https://" not in action.body


def test_merchant_fact_isolation():
    """Verify facts from Merchant A do not leak to Merchant B in the same category."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))

    m_a = {
        "merchant_id": "m_a_delhi",
        "category_slug": "dentists",
        "identity": {"name": "Dr. Meera Clinic", "owner_first_name": "Meera", "locality": "Lajpat Nagar"},
        "performance": {"views": 2410},
        "offers": [{"id": "o1", "title": "Dental Cleaning @ ₹299", "status": "active"}]
    }

    m_b = {
        "merchant_id": "m_b_mumbai",
        "category_slug": "dentists",
        "identity": {"name": "Bharat Dental Care", "owner_first_name": "Bharat", "locality": "Andheri West"},
        "performance": {"views": 980},
        "offers": [{"id": "o2", "title": "Deep Cleaning @ ₹499", "status": "active"}]
    }

    trg_a = {"id": "trg_a", "kind": "perf_dip", "scope": "merchant", "merchant_id": "m_a_delhi", "urgency": 3, "suppression_key": "trg_a"}
    trg_b = {"id": "trg_b", "kind": "perf_dip", "scope": "merchant", "merchant_id": "m_b_mumbai", "urgency": 3, "suppression_key": "trg_b"}

    sig_a = extract_normalized_signals(trigger=trg_a, merchant=m_a, category=cat_payload)
    sig_b = extract_normalized_signals(trigger=trg_b, merchant=m_b, category=cat_payload)

    dec_a = select_best_decision(sig_a)
    dec_b = select_best_decision(sig_b)

    act_a = compose_message_from_decision(dec_a)
    act_b = compose_message_from_decision(dec_b)

    assert "2410" in act_a.body
    assert "980" not in act_a.body
    assert "Bharat" not in act_a.body

    assert "980" in act_b.body
    assert "2410" not in act_b.body
    assert "Meera" not in act_b.body


def test_adversarial_missing_data_no_hallucination():
    """Verify that missing offers/prices/numbers never result in manufactured text."""
    cat_payload = json.load(open(DATASET_DIR / "categories" / "dentists.json"))

    m_bare = {
        "merchant_id": "m_bare",
        "category_slug": "dentists",
        "identity": {"name": "Bare Dental", "locality": "Saket"},
        "performance": {},  # Missing views & calls
        "offers": []        # Missing offers
    }

    trg = {"id": "trg_bare", "kind": "perf_dip", "scope": "merchant", "merchant_id": "m_bare", "urgency": 2, "suppression_key": "trg_bare"}

    signals = extract_normalized_signals(trigger=trg, merchant=m_bare, category=cat_payload)
    decision = select_best_decision(signals)
    assert decision is not None

    action = compose_message_from_decision(decision)
    # Check that no random numbers (like fake price or views) were invented
    is_valid, err = validate_action(action, decision)
    assert is_valid is True, err
    assert "₹" not in action.body  # No fake price
