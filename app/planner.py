import json
import re

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import ValidationError

from app.budget import revision_instruction, summarize_costs
from app.knowledge import KnowledgeBase
from app.schemas import Itinerary, PlanResult, TripRequest

SYSTEM_PROMPT = """You are a careful travel planner for trips in India.
Reply with one JSON object only, with no text before or after it, matching this schema:
{schema}

Rules:
- All costs are whole numbers in INR and are totals for the whole group.
- Create exactly the number of days requested, numbered from 1.
- Every day has at least one activity. time_of_day is morning, afternoon or evening.
- Use the travel notes when they are relevant. If the notes do not cover something, give a sensible estimate.
- The total of all costs must not exceed the budget."""


class PlanningError(RuntimeError):
    """The model did not produce a valid itinerary within the allowed attempts."""


def message_text(message: BaseMessage) -> str:
    """Chat models can return plain text or a list of content blocks."""
    if isinstance(message.content, str):
        return message.content
    return "".join(
        block if isinstance(block, str) else block.get("text", "")
        for block in message.content
    )


def extract_json(text: str) -> dict:
    """Pull the JSON object out of a reply, tolerating markdown fences or extra words around it."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in the reply")
    return json.loads(candidate[start : end + 1])


def check_days(itinerary: Itinerary, expected_days: int) -> None:
    numbers = [day.day for day in itinerary.days]
    if numbers != list(range(1, expected_days + 1)):
        raise ValueError(f"expected days numbered 1 to {expected_days}, got {numbers}")


def parse_itinerary(text: str, expected_days: int) -> Itinerary:
    itinerary = Itinerary.model_validate(extract_json(text))
    check_days(itinerary, expected_days)
    return itinerary


class TravelPlanner:
    """Retrieve notes, draft an itinerary, repair invalid output, then revise it until it fits the budget."""

    def __init__(self, llm: BaseChatModel, knowledge: KnowledgeBase, max_parse_attempts: int = 3, max_budget_revisions: int = 2):
        self.llm = llm
        self.knowledge = knowledge
        self.max_parse_attempts = max_parse_attempts
        self.max_budget_revisions = max_budget_revisions

    def plan(self, request: TripRequest) -> PlanResult:
        interests = ", ".join(request.interests) or "general sightseeing"
        chunks = self.knowledge.search(request.destination, f"{interests}, where to stay, food, costs, getting around")
        notes = "\n\n".join(chunk.page_content for chunk in chunks) or "No notes available for this destination."

        messages: list[BaseMessage] = [
            SystemMessage(SYSTEM_PROMPT.format(schema=json.dumps(Itinerary.model_json_schema()))),
            HumanMessage(
                f"Travel notes:\n{notes}\n\n"
                f"Plan a {request.days}-day trip to {request.destination} for {request.travellers} traveller(s). "
                f"Total budget: {request.budget_inr} INR. Interests: {interests}."
            ),
        ]

        calls = 0
        revisions = 0
        while True:
            itinerary, used = self._generate_valid(messages, request.days)
            calls += used
            summary = summarize_costs(itinerary, request.budget_inr)
            if summary.within_budget or revisions >= self.max_budget_revisions:
                return PlanResult(
                    itinerary=itinerary,
                    cost=summary,
                    sources=[chunk.metadata["source"] for chunk in chunks],
                    parse_attempts=calls,
                    budget_revisions=revisions,
                )
            revisions += 1
            messages.append(AIMessage(itinerary.model_dump_json()))
            messages.append(HumanMessage(revision_instruction(summary)))

    def _generate_valid(self, messages: list[BaseMessage], expected_days: int) -> tuple[Itinerary, int]:
        """Call the model until the reply passes validation. On failure, send the error back so it can fix it."""
        attempt_messages = list(messages)
        last_error = ""
        for attempt in range(1, self.max_parse_attempts + 1):
            reply = self.llm.invoke(attempt_messages)
            text = message_text(reply)
            try:
                return parse_itinerary(text, expected_days), attempt
            except (ValueError, ValidationError) as error:
                last_error = str(error)
                attempt_messages.append(AIMessage(text))
                attempt_messages.append(
                    HumanMessage(f"That reply was not valid: {last_error}\nReply again with the corrected JSON object only.")
                )
        raise PlanningError(f"no valid itinerary after {self.max_parse_attempts} attempts: {last_error}")
