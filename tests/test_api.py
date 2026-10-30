from conftest import itinerary_json
from fastapi.testclient import TestClient

from app.api import app, get_planner
from evals.measure_reliability import run_eval
from app.schemas import TripRequest

PAYLOAD = {"destination": "Goa", "days": 2, "travellers": 2, "budget_inr": 10000, "interests": ["beaches"]}
client = TestClient(app)


def override(planner):
    app.dependency_overrides[get_planner] = lambda: planner


def teardown_function():
    app.dependency_overrides.clear()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_plan_returns_itinerary_and_costs(make_planner):
    override(make_planner(itinerary_json()))
    response = client.post("/plan", json=PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert len(body["itinerary"]["days"]) == 2
    assert body["cost"]["total_inr"] == 3600
    assert body["cost"]["within_budget"] is True


def test_plan_rejects_bad_input(make_planner):
    override(make_planner(itinerary_json()))
    assert client.post("/plan", json={**PAYLOAD, "days": 0}).status_code == 422


def test_plan_reports_model_failure_as_502(make_planner):
    override(make_planner("bad", "bad", "bad"))
    assert client.post("/plan", json=PAYLOAD).status_code == 502


def test_eval_counts_repairs_and_failures(make_planner):
    good = itinerary_json()
    planner = make_planner(good, "bad", good, "bad", "bad", "bad", max_parse_attempts=3)
    request = TripRequest(**PAYLOAD)
    results = run_eval(planner, [request], repeats=3)
    assert results["runs"] == 3
    assert results["valid_itineraries"] == 2
    assert results["valid_with_no_repair"] == 1
    assert len(results["failures"]) == 1
