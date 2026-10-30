from typing import Literal

from pydantic import BaseModel, Field


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, examples=["Goa"])
    days: int = Field(ge=1, le=14, examples=[3])
    travellers: int = Field(default=1, ge=1, le=10)
    budget_inr: int = Field(gt=0, description="Total budget for the whole group, excluding travel to the destination")
    interests: list[str] = Field(default_factory=list, examples=[["beaches", "food"]])


class Activity(BaseModel):
    name: str = Field(min_length=1)
    time_of_day: Literal["morning", "afternoon", "evening"]
    description: str = Field(min_length=1)
    cost_inr: int = Field(ge=0, description="Total cost for the whole group")


class DayPlan(BaseModel):
    day: int = Field(ge=1)
    title: str = Field(min_length=1)
    activities: list[Activity] = Field(min_length=1)
    stay_cost_inr: int = Field(ge=0)
    food_cost_inr: int = Field(ge=0)
    local_transport_cost_inr: int = Field(ge=0)

    @property
    def total_inr(self) -> int:
        activities = sum(a.cost_inr for a in self.activities)
        return activities + self.stay_cost_inr + self.food_cost_inr + self.local_transport_cost_inr


class Itinerary(BaseModel):
    destination: str = Field(min_length=1)
    days: list[DayPlan] = Field(min_length=1)
    tips: list[str] = Field(default_factory=list)


class CostSummary(BaseModel):
    activities_inr: int
    stay_inr: int
    food_inr: int
    local_transport_inr: int
    total_inr: int
    budget_inr: int
    remaining_inr: int
    within_budget: bool


class PlanResult(BaseModel):
    itinerary: Itinerary
    cost: CostSummary
    sources: list[str]
    parse_attempts: int = Field(description="LLM calls used to reach a valid itinerary, across all revisions")
    budget_revisions: int
