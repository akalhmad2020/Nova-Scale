from app.ai.application.services.chunk_text import ChunkTextService


def test_chunk_text_creates_document_chunks() -> None:
    service = ChunkTextService(
        chunk_size=30,
        chunk_overlap=5,
    )

    chunks = service.execute(
        document_id="document-1",
        text=(
            "NovaScale manages shipments and logistics operations. "
            "It also manages billing and payments."
        ),
    )

    assert len(chunks) > 1

    for index, chunk in enumerate(chunks):
        assert chunk.id == f"document-1:{index}"
        assert chunk.document_id == "document-1"
        assert chunk.chunk_index == index
        assert chunk.content


def test_chunk_text_returns_no_chunks_for_empty_text() -> None:
    service = ChunkTextService()

    chunks = service.execute(
        document_id="document-1",
        text="",
    )

    assert chunks == ()
