from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ai.domain.rag_models import DocumentChunk


class ChunkTextService:
    def __init__(
        self,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def execute(
        self,
        *,
        document_id: str,
        text: str,
    ) -> tuple[DocumentChunk, ...]:
        chunks = self._splitter.split_text(text)

        return tuple(
            DocumentChunk(
                id=f"{document_id}:{index}",
                document_id=document_id,
                content=content,
                chunk_index=index,
            )
            for index, content in enumerate(chunks)
        )
