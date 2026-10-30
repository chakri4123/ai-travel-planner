from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore


def split_guide(path: Path) -> list[Document]:
    """Split a markdown guide into one chunk per '## ' section, keeping the guide title for context."""
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].removeprefix("# ").strip()
    destination = path.stem.lower()

    sections: list[list[str]] = []
    for line in lines[1:]:
        if line.startswith("## "):
            sections.append([line.removeprefix("## ").strip()])
        elif sections and line.strip():
            sections[-1].append(line.strip())

    return [
        Document(
            page_content=f"{title} - {section[0]}\n" + "\n".join(section[1:]),
            metadata={"destination": destination, "section": section[0], "source": f"{path.name}#{section[0]}"},
        )
        for section in sections
        if len(section) > 1
    ]


class KnowledgeBase:
    def __init__(self, directory: Path, embeddings: Embeddings, k: int = 4):
        self.k = k
        self.chunks = [chunk for path in sorted(directory.glob("*.md")) for chunk in split_guide(path)]
        self.destinations = {chunk.metadata["destination"] for chunk in self.chunks}
        self.store = InMemoryVectorStore(embeddings)
        if self.chunks:
            self.store.add_documents(self.chunks)

    def search(self, destination: str, query: str) -> list[Document]:
        """Return the closest chunks for this destination, or nothing if we have no guide for it."""
        key = destination.strip().lower()
        if key not in self.destinations:
            return []
        return self.store.similarity_search(query, k=self.k, filter=lambda doc: doc.metadata["destination"] == key)
