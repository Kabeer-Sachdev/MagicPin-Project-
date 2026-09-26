from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.engine.composer import compose_message_from_decision
from app.engine.models import Decision
from app.engine.ranking import select_best_decision
from app.engine.signals import extract_normalized_signals
from app.engine.validator import validate_action
from app.state import store

DATASET_DIR = Path(__file__).parent.parent / "dataset"


def run_evaluation_harness() -> Dict[str, Any]:
    store.contexts.clear()
    store.suppressions.clear()
    store.conversations.clear()

    report_entries = []
    categories = ["dentists", "salons", "restaurants", "gyms", "pharmacies"]

    start_time = time.time()
    total_evaluated = 0
    total_passed = 0

    for cat_slug in categories:
        cat_file = DATASET_DIR / "categories" / f"{cat_slug}.json"
        cat_payload = json.load(open(cat_file))

        # Test case 1: Primary Demand Signal
        trg_demand = {
            "id": f"trg_eval_{cat_slug}_demand",
            "kind": "research_digest" if cat_slug == "dentists" else "perf_dip",
            "scope": "merchant",
            "source": "external",
            "merchant_id": f"m_eval_{cat_slug}",
            "payload": {"category": cat_slug},
            "urgency": 3,
            "suppression_key": f"eval:{cat_slug}:demand"
        }

        m_payload = {
            "merchant_id": f"m_eval_{cat_slug}",
            "category_slug": cat_slug,
            "identity": {"name": f"Eval {cat_slug.capitalize()} Biz", "owner_first_name": "Valued Partner", "locality": "Central"},
            "subscription": {"status": "active", "days_remaining": 45},
            "performance": {"window_days": 30, "views": 1850, "calls": 24, "ctr": 0.035},
            "offers": [{"id": "o_eval", "title": "Special Offer @ ₹299", "status": "active"}],
            "signals": []
        }

        signals = extract_normalized_signals(trigger=trg_demand, merchant=m_payload, category=cat_payload)
        decision = select_best_decision(signals)

        total_evaluated += 1
        entry = {
            "scenario_id": f"eval_{cat_slug}_demand",
            "category": cat_slug,
            "merchant_id": f"m_eval_{cat_slug}",
            "selected_signal": decision.signal_type if decision else None,
            "decision_score": decision.score if decision else 0.0,
            "message": None,
            "cta": None,
            "suppression_key": decision.suppression_key if decision else None,
            "validation_result": False,
            "failure_type": None
        }

        if decision:
            action = compose_message_from_decision(decision)
            is_valid, err = validate_action(action, decision)
            entry["message"] = action.body
            entry["cta"] = action.cta
            entry["validation_result"] = is_valid
            if is_valid:
                total_passed += 1
            else:
                entry["failure_type"] = f"ValidationFailed: {err}"
        else:
            entry["failure_type"] = "NoDecisionSelected"

        report_entries.append(entry)

    duration = time.time() - start_time
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_evaluated": total_evaluated,
        "total_passed": total_passed,
        "pass_rate_pct": round((total_passed / total_evaluated) * 100.0, 2) if total_evaluated > 0 else 0,
        "duration_seconds": round(duration, 3),
        "report_entries": report_entries
    }

    # Save machine-readable evaluation report
    report_file = Path(__file__).parent.parent / "evaluation_report.json"
    with open(report_file, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    res = run_evaluation_harness()
    print(f"Evaluation Complete: {res['total_passed']}/{res['total_evaluated']} Passed ({res['pass_rate_pct']}%) in {res['duration_seconds']}s")
