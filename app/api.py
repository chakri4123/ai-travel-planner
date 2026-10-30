from fastapi import Depends, FastAPI, HTTPException

from app.factory import MissingApiKey, build_planner
from app.planner import PlanningError, TravelPlanner
from app.schemas import PlanResult, TripRequest

app = FastAPI(title="AI Travel Planner", version="1.0.0")


def get_planner() -> TravelPlanner:
    try:
        return build_planner()
    except MissingApiKey as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/plan", response_model=PlanResult)
def create_plan(request: TripRequest, planner: TravelPlanner = Depends(get_planner)) -> PlanResult:
    try:
        return planner.plan(request)
    except PlanningError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
