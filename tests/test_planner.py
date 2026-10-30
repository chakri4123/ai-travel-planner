import pytest
from conftest import itinerary_json

from app.budget import summarize_costs
from app.knowledge import split_guide
from app.planner import PlanningError, extract_json, parse_itinerary
from app.schemas import Itinerary, TripRequest
from conftest import GUIDES

REQUEST = TripRequest(destination="Goa", days=2, travellers=2, budget_inr=10000, interests=["beaches"])


def test_extract_json_handles_fences_and_extra_text():
    assert extract_json('Sure!\n```json\n{"a": 1}\n```\nEnjoy') == {"a": 1}
    assert extract_json('Here you go {"a": 1} done') == {"a": 1}


def test_extract_json_rejects_text_without_json():
    with pytest.raises(ValueError):
        extract_json("I cannot help with that")


def test_parse_rejects_wrong_day_count():
    with pytest.raises(ValueError, match="expected days"):
        parse_itinerary(itinerary_json(days=3), expected_days=2)


def test_costs_are_recalculated_in_code():
    itinerary = Itinerary.model_validate_json(itinerary_json(days=2, stay=1000))
    summary = summarize_costs(itinerary, budget_inr=3000)
    assert summary.total_inr == 2 * (100 + 1000 + 500 + 200)
    assert summary.remaining_inr == 3000 - 3600
    assert summary.within_budget is False


def test_valid_reply_needs_one_call(make_planner):
    result = make_planner(itinerary_json()).plan(REQUEST)
    assert result.parse_attempts == 1
    assert result.budget_revisions == 0
    assert result.cost.within_budget
    assert result.sources and all(source.startswith("goa.md#") for source in result.sources)


def test_invalid_reply_is_repaired(make_planner):
    result = make_planner("not json at all", itinerary_json()).plan(REQUEST)
    assert result.parse_attempts == 2


def test_gives_up_after_max_attempts(make_planner):
    planner = make_planner("bad", "still bad", "worse", max_parse_attempts=3)
    with pytest.raises(PlanningError):
        planner.plan(REQUEST)


def test_over_budget_plan_is_revised(make_planner):
    result = make_planner(itinerary_json(stay=9000), itinerary_json(stay=1000)).plan(REQUEST)
    assert result.budget_revisions == 1
    assert result.cost.within_budget


def test_stops_revising_and_reports_over_budget(make_planner):
    expensive = itinerary_json(stay=9000)
    result = make_planner(expensive, expensive, expensive, max_budget_revisions=2).plan(REQUEST)
    assert result.budget_revisions == 2
    assert result.cost.within_budget is False


def test_unknown_destination_still_plans_without_notes(make_planner):
    request = REQUEST.model_copy(update={"destination": "Hampi"})
    result = make_planner(itinerary_json(destination="Hampi")).plan(request)
    assert result.sources == []


def test_retrieval_stays_inside_the_destination(knowledge):
    chunks = knowledge.search("jaipur", "forts and food")
    assert chunks and all(chunk.metadata["destination"] == "jaipur" for chunk in chunks)


def test_every_guide_splits_into_sections():
    for path in GUIDES.glob("*.md"):
        assert len(split_guide(path)) >= 5
