from app.schemas import CostSummary, Itinerary


def summarize_costs(itinerary: Itinerary, budget_inr: int) -> CostSummary:
    """Recalculate costs in code, so the totals never depend on the model's arithmetic."""
    activities = sum(a.cost_inr for day in itinerary.days for a in day.activities)
    stay = sum(day.stay_cost_inr for day in itinerary.days)
    food = sum(day.food_cost_inr for day in itinerary.days)
    transport = sum(day.local_transport_cost_inr for day in itinerary.days)
    total = activities + stay + food + transport
    return CostSummary(
        activities_inr=activities,
        stay_inr=stay,
        food_inr=food,
        local_transport_inr=transport,
        total_inr=total,
        budget_inr=budget_inr,
        remaining_inr=budget_inr - total,
        within_budget=total <= budget_inr,
    )


def revision_instruction(summary: CostSummary) -> str:
    """Tell the model where the money went, so it can cut the largest categories first."""
    over_by = summary.total_inr - summary.budget_inr
    return (
        f"The itinerary costs {summary.total_inr} INR but the budget is {summary.budget_inr} INR, "
        f"so it is over by {over_by} INR. Current split: stay {summary.stay_inr}, food {summary.food_inr}, "
        f"activities {summary.activities_inr}, local transport {summary.local_transport_inr}. "
        "Rewrite the itinerary so the total fits the budget, cutting the largest categories first "
        "while keeping the same number of days."
    )
