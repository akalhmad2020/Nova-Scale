from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    id: str
    document_id: str
    content: str
    chunk_index: int


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    chunk: DocumentChunk
    embedding: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True, slots=True)
class RAGAnswer:
    content: str
    model: str
    sources: tuple[RetrievedChunk, ...]
