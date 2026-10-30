"""Measure how often the planner returns a valid itinerary, using the real model.

Run from the repo root:  python -m evals.measure_reliability --repeats 5
Writes evals/results.json. Each run costs API calls.
"""
import argparse
import json
import time
from pathlib import Path

from app.config import Settings
from app.planner import PlanningError, TravelPlanner
from app.schemas import TripRequest

HERE = Path(__file__).resolve().parent


def run_eval(planner: TravelPlanner, requests: list[TripRequest], repeats: int, delay_seconds: float = 0) -> dict:
    total = valid = first_try = within_budget = 0
    failures = []
    api_errors = []
    for request in requests:
        for _ in range(repeats):
            time.sleep(delay_seconds)
            try:
                result = planner.plan(request)
            except PlanningError as error:
                total += 1
                failures.append({"destination": request.destination, "error": str(error)[:300]})
                continue
            except Exception as error:  # Outages and rate limits say nothing about output quality, so they are not scored.
                api_errors.append({"destination": request.destination, "error": str(error)[:300]})
                continue
            total += 1
            valid += 1
            first_try += result.parse_attempts == 1 + result.budget_revisions
            within_budget += result.cost.within_budget
    return {
        "runs": total,
        "valid_itineraries": valid,
        "valid_rate": round(valid / total, 4) if total else 0.0,
        "valid_with_no_repair": first_try,
        "no_repair_rate": round(first_try / total, 4) if total else 0.0,
        "within_budget": within_budget,
        "within_budget_rate": round(within_budget / total, 4) if total else 0.0,
        "failures": failures,
        "api_errors_not_scored": api_errors,
    }


def main() -> None:
    from app.factory import build_planner

    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--delay", type=float, default=6.0, help="Seconds to wait before each run, to respect rate limits")
    args = parser.parse_args()

    lines = (HERE / "requests.jsonl").read_text(encoding="utf-8").splitlines()
    requests = [TripRequest.model_validate_json(line) for line in lines if line.strip()]
    results = {"model": Settings().chat_model, **run_eval(build_planner(), requests, args.repeats, args.delay)}

    (HERE / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    summary = {key: value for key, value in results.items() if key not in ("failures", "api_errors_not_scored")}
    summary["api_errors_not_scored"] = len(results["api_errors_not_scored"])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
