from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple
from app.categories import get_category_strategy
from app.engine.models import Decision, Opportunity, Signal
from app.engine.scoring_weights import get_weight
from app.state import store

logger = logging.getLogger("vera.engine.ranking")


def deduplicate_signals(signals: List[Signal]) -> List[Opportunity]:
    """
    Groups raw extracted signals by merchant_id and signal_type to deduplicate opportunities.
    """
    grouped: Dict[Tuple[str, str], List[Signal]] = {}
    for sig in signals:
        key = (sig.merchant_id, sig.type)
        grouped.setdefault(key, []).append(sig)

    opportunities: List[Opportunity] = []
    for (m_id, s_type), sig_list in grouped.items():
        # Sort by urgency descending
        sig_list.sort(key=lambda s: -s.urgency)
        primary = sig_list[0]
        supporting = sig_list[1:]

        opp = Opportunity(
            opportunity_id=f"opp_{m_id}_{primary.signal_id}",
            merchant_id=m_id,
            primary_signal=primary,
            supporting_signals=supporting,
            evidence=primary.evidence,
            recommended_action=f"action_{s_type}",
            suppression_key=primary.suppression_key
        )
        opportunities.append(opp)

    return opportunities


def score_opportunity(opp: Opportunity) -> float:
    """
    Computes a deterministic score for an opportunity using weighted factors.
    """
    sig = opp.primary_signal

    # Check suppression
    if store.is_suppressed(sig.suppression_key):
        return -100.0  # Completely filter out suppressed opportunity

    strat = get_category_strategy(sig.category)
    cat_weights = strat.get_signal_weights() if hasattr(strat, "get_signal_weights") else {}
    cat_fit_weight = cat_weights.get(sig.type, 5.0)

    base_score = float(sig.urgency) * get_weight("base_trigger_strength", 2.0)
    recency_contrib = sig.recency_score * get_weight("recency", 4.0)
    actionability_contrib = sig.actionability_score * get_weight("actionability", 6.0)
    specificity_contrib = sig.specificity_score * get_weight("specificity", 5.0)
    relevance_contrib = sig.relevance_score * get_weight("merchant_relevance", 5.0)

    # Magnitude contribution if delta change exists
    magnitude_contrib = 0.0
    if sig.change_pct is not None:
        magnitude_contrib = min(5.0, abs(sig.change_pct) / 10.0) * get_weight("magnitude", 1.0)

    # Customer relevance boost if customer-scoped
    customer_contrib = 0.0
    if sig.scope == "customer":
        customer_contrib = get_weight("customer_relevance", 6.0)

    total_score = (
        base_score +
        recency_contrib +
        actionability_contrib +
        specificity_contrib +
        relevance_contrib +
        cat_fit_weight +
        magnitude_contrib +
        customer_contrib
    )

    opp.score = round(total_score, 2)
    return opp.score


def select_best_decision(signals: List[Signal]) -> Optional[Decision]:
    """
    Deduplicates, scores, ranks opportunities, selects ONE primary opportunity,
    and returns a structured Decision object with explicit rationale.
    """
    if not signals:
        return None

    opportunities = deduplicate_signals(signals)
    scored_opps: List[Tuple[Opportunity, float]] = []

    for opp in opportunities:
        score = score_opportunity(opp)
        if score > 0:
            scored_opps.append((opp, score))

    if not scored_opps:
        logger.debug("No unsuppressed positive scoring opportunities found.")
        return None

    # Deterministic sort by score descending, then opportunity_id ascending
    scored_opps.sort(key=lambda item: (-item[1], item[0].opportunity_id))
    best_opp, best_score = scored_opps[0]
    sig = best_opp.primary_signal

    # Construct explicit rationale explaining WHY this opportunity was selected
    reasons = [
        f"Signal type '{sig.type}' matched category strategy '{sig.category}'",
        f"Urgency level {sig.urgency} (base score: {sig.urgency * 2.0:.1f})",
        f"Actionability score: {sig.actionability_score:.2f}",
        f"Specificity score: {sig.specificity_score:.2f}",
    ]
    if sig.change_pct is not None:
        reasons.append(f"Measured delta change: {sig.change_pct:.1f}%")
    if sig.scope == "customer":
        reasons.append(f"Customer-scoped opportunity for customer '{sig.customer_id}'")

    rationale_str = f"Selected '{sig.type}' (Score: {best_score:.1f}) because: " + "; ".join(reasons) + "."

    logger.debug(f"Selected decision: {best_opp.opportunity_id} with score {best_score}")

    return Decision(
        opportunity_id=best_opp.opportunity_id,
        merchant_id=sig.merchant_id,
        customer_id=sig.customer_id,
        signal_type=sig.type,
        score=best_score,
        primary_evidence=sig.evidence,
        supporting_evidence=[s.evidence for s in best_opp.supporting_signals],
        recommended_action=best_opp.recommended_action,
        category_strategy=sig.category,
        suppression_key=sig.suppression_key,
        rationale=rationale_str,
        send_as="merchant_on_behalf" if sig.scope == "customer" else "vera",
        trigger_id=sig.signal_id
    )
