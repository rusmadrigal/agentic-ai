"""Deterministic pricing / promo / inventory suggestions (MVP simulated layer)."""

from __future__ import annotations

from typing import Optional

from app.models.simulated import SimulatedDecisionsBlock


def compute_simulated_decisions(
    price_usd: float,
    stock: Optional[int],
    competitors: list[tuple[str, float]],
) -> SimulatedDecisionsBlock:
    comp_prices = [p for _, p in competitors if p is not None and p >= 0]
    avg = sum(comp_prices) / len(comp_prices) if comp_prices else price_usd

    if price_usd > avg * 1.02:
        pricing_strategy = "slightly_under_market"
        recommended_price = round(min(price_usd * 0.97, avg * 0.98), 2)
        promotion = "Offer a time-boxed ~10% discount or loyalty tier to close the gap vs. peers."
        reasoning = (
            f"Your list price ({price_usd:.2f}) sits above the competitor average (~{avg:.2f}). "
            "A modest reduction improves competitiveness while preserving margin vs. deep discounting."
        )
    elif price_usd < avg * 0.98:
        pricing_strategy = "premium_or_lift"
        recommended_price = round(max(price_usd * 1.05, avg * 1.02), 2)
        promotion = "Lead with value props and bundles; avoid broad sitewide markdowns."
        reasoning = (
            f"Price ({price_usd:.2f}) is below peer average (~{avg:.2f}). "
            "There is room to lift price or reinforce premium positioning."
        )
    else:
        pricing_strategy = "parity"
        recommended_price = round(price_usd, 2)
        promotion = "Keep targeted promos (email/SMS) rather than blanket discounts."
        reasoning = (
            f"Price is broadly in line with the competitor average (~{avg:.2f}). "
            "Maintain parity while testing incremental upsell."
        )

    if stock is not None:
        if stock <= 0:
            inventory_action = "Restock or pause promos until availability is restored."
        elif stock < 25:
            inventory_action = "Increase stock or tighten promos until supply stabilizes."
        elif stock > 800:
            inventory_action = "Accelerate turns: prioritize bundles, clearance, or channel-specific pushes."
        else:
            inventory_action = "Hold replenishment steady; monitor weekly sell-through vs. pricing moves."
    else:
        inventory_action = "Align inventory coverage with the pricing scenario above and next month's forecast."

    return SimulatedDecisionsBlock(
        pricing_strategy=pricing_strategy,
        recommended_price=recommended_price,
        promotion=promotion,
        inventory_action=inventory_action,
        reasoning=reasoning,
    )
