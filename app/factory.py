from functools import lru_cache

from app.config import Settings
from app.knowledge import KnowledgeBase
from app.planner import TravelPlanner


class MissingApiKey(RuntimeError):
    pass


@lru_cache
def build_planner() -> TravelPlanner:
    settings = Settings()
    if not settings.google_api_key:
        raise MissingApiKey("GOOGLE_API_KEY is not set. Copy .env.example to .env and add your key.")

    # Imported here so tests and the UI do not need Gemini credentials or the import cost.
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

    llm = ChatGoogleGenerativeAI(
        model=settings.chat_model,
        temperature=settings.temperature,
        google_api_key=settings.google_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=2,
    )
    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )
    knowledge = KnowledgeBase(settings.knowledge_dir, embeddings, k=settings.retrieval_k)
    return TravelPlanner(llm, knowledge, settings.max_parse_attempts, settings.max_budget_revisions)
