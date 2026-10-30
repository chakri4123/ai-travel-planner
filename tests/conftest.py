import json
from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.knowledge import KnowledgeBase
from app.planner import TravelPlanner

GUIDES = Path(__file__).resolve().parent.parent / "data" / "destinations"


def itinerary_json(days: int = 2, stay: int = 1000, destination: str = "Goa") -> str:
    return json.dumps(
        {
            "destination": destination,
            "days": [
                {
                    "day": number,
                    "title": f"Day {number}",
                    "activities": [
                        {"name": "Beach", "time_of_day": "morning", "description": "Walk on the beach", "cost_inr": 100}
                    ],
                    "stay_cost_inr": stay,
                    "food_cost_inr": 500,
                    "local_transport_cost_inr": 200,
                }
                for number in range(1, days + 1)
            ],
            "tips": ["Carry sunscreen"],
        }
    )


@pytest.fixture
def knowledge() -> KnowledgeBase:
    return KnowledgeBase(GUIDES, DeterministicFakeEmbedding(size=32), k=3)


@pytest.fixture
def make_planner(knowledge):
    def build(*replies: str, **kwargs) -> TravelPlanner:
        return TravelPlanner(FakeListChatModel(responses=list(replies)), knowledge, **kwargs)

    return build
