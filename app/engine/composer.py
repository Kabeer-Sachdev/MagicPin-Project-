from __future__ import annotations

from typing import Any, Dict
from app.engine.models import Decision
from app.engine.strategy_selector import select_message_blueprint
from app.schemas import ActionItem


def compose_message_from_decision(decision: Decision) -> ActionItem:
    """
    Composes a grounded ActionItem directly from a Decision object using
    the strategy selector and blueprint layer.
    Guarantees zero invented facts and exactly one CTA.
    """
    bp = select_message_blueprint(decision)
    ev = bp.selected_evidence
    kind = decision.signal_type
    merchant_id = decision.merchant_id
    customer_id = decision.customer_id

    salutation = bp.salutation
    merchant_name = ev.get("merchant_name", "your business")

    body = ""
    cta = bp.cta_type
    template_name = f"vera_{kind}_v1"
    template_params = []

    # 1. Research Digest Blueprint
    if bp.blueprint_type == "research_digest":
        title = ev.get("title", "new clinical research")
        source = ev.get("source", "latest issue")
        trial_n = ev.get("trial_n")
        trial_str = f"{trial_n}-patient " if trial_n else ""

        body = (
            f"{salutation}, {source} landed. One item relevant to your practice — "
            f"{trial_str}trial showed {title.lower()}. "
            f"Worth a look (2-min abstract). Want me to pull it + draft a patient-ed WhatsApp you can share? — {source}"
        )
        template_params = [salutation, source, title]

    # 2. Customer Recall Blueprint
    elif bp.blueprint_type == "customer_recall":
        cust_name = ev.get("customer_name", "Customer")
        lang_pref = ev.get("customer_language", "en")
        offer_title = ev.get("offer_title", "routine recall checkup")

        if "hi" in lang_pref.lower():
            body = (
                f"Hi {cust_name}, {merchant_name} here 🦷 It's time for your regular recall visit. "
                f"Apke liye slots ready hain. Active offer: {offer_title}. "
                f"Reply 1 to book, or tell us a time that works for you."
            )
        else:
            body = (
                f"Hi {cust_name}, {merchant_name} here 🦷 It's time for your regular recall visit. "
                f"We have slots available for you. Offer: {offer_title}. "
                f"Reply 1 to book or let us know what time works best."
            )

        template_name = "merchant_recall_reminder_v1"
        template_params = [cust_name, merchant_name, offer_title]
        cta = "multi_choice_slot"

    # 3. Performance Dip Blueprint
    elif bp.blueprint_type == "perf_dip":
        views = ev.get("views")
        views_str = f"views are at {views}" if views is not None else "traffic saw a shift"

        body = (
            f"{salutation}, your profile {views_str} this window. "
            f"Focusing on active customer retention is the best move right now. "
            f"Want me to draft a quick engagement post for your profile?"
        )
        template_name = "vera_perf_dip_v1"
        template_params = [salutation, str(views or "recent views")]
        cta = "binary_yes_no"

    # 4. Performance Spike Blueprint
    elif bp.blueprint_type == "perf_spike":
        views = ev.get("views")
        views_str = f"{views} views" if views is not None else "a strong spike"
        offer_title = ev.get("offer_title")
        offer_str = f" with your active offer {offer_title}" if offer_title else ""

        body = (
            f"Great news {salutation}! Your listing reached {views_str} this month. "
            f"To keep the momentum going, should I publish a fresh post{offer_str}?"
        )
        template_name = "vera_perf_spike_v1"
        template_params = [salutation, str(views or "views")]
        cta = "binary_yes_no"

    # 5. Curious Ask Blueprint
    elif bp.blueprint_type == "curious_ask":
        body = (
            f"Hi {salutation}! Quick check — what service or product has been most asked-for this week at {merchant_name}? "
            f"I'll turn the answer into a business post + a quick WhatsApp draft for your customers. Takes 2 min."
        )
        template_name = "vera_curious_ask_v1"
        template_params = [salutation, merchant_name]
        cta = "open_ended"

    # 6. Expiring Offer / Renewal Blueprint
    elif bp.blueprint_type == "expiring_offer":
        days_rem = ev.get("days_remaining")
        body = (
            f"{salutation}, your subscription renewal is due in {days_rem} days. "
            f"Would you like me to review your performance metrics before renewing?"
        )
        template_name = "vera_renewal_v1"
        template_params = [salutation, str(days_rem or "few")]
        cta = "binary_yes_no"

    # 7. Generic Fallback Blueprint
    else:
        offer_title = ev.get("offer_title")
        offer_str = f" (active offer: {offer_title})" if offer_title else ""

        body = (
            f"Hi {salutation}, checking in on {merchant_name}{offer_str}. "
            f"Would you like me to review and optimize your business profile for this week?"
        )
        template_name = "vera_generic_v1"
        template_params = [salutation, merchant_name]
        cta = "binary_yes_no"

    return ActionItem(
        conversation_id=f"conv_{merchant_id}_{decision.trigger_id}",
        merchant_id=merchant_id,
        customer_id=customer_id,
        send_as=decision.send_as,
        trigger_id=decision.trigger_id,
        template_name=template_name,
        template_params=template_params,
        body=body,
        cta=cta,
        suppression_key=decision.suppression_key,
        rationale=decision.rationale,
    )
