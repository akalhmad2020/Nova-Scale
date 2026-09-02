from pathlib import Path

import pytest

from app.ai.infrastructure.document_content.local_text_reader import (
    LocalTextDocumentContentReader,
)


@pytest.mark.asyncio
async def test_local_text_reader_reads_text_file(
    tmp_path: Path,
) -> None:
    document_directory = tmp_path / "documents"
    document_directory.mkdir()

    document_path = document_directory / "shipment.txt"
    document_path.write_text(
        "Shipment NOVA-100 is in transit.",
        encoding="utf-8",
    )

    reader = LocalTextDocumentContentReader(
        storage_root=tmp_path,
    )

    text = await reader.read_text(
        storage_key="documents/shipment.txt",
        content_type="text/plain",
    )

    assert text == "Shipment NOVA-100 is in transit."


@pytest.mark.asyncio
async def test_local_text_reader_rejects_unsupported_content_type(
    tmp_path: Path,
) -> None:
    reader = LocalTextDocumentContentReader(
        storage_root=tmp_path,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported document content type",
    ):
        await reader.read_text(
            storage_key="documents/shipment.pdf",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_local_text_reader_rejects_path_outside_storage_root(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    storage_root.mkdir()

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text(
        "secret",
        encoding="utf-8",
    )

    reader = LocalTextDocumentContentReader(
        storage_root=storage_root,
    )

    with pytest.raises(
        ValueError,
        match="Storage key resolves outside storage root",
    ):
        await reader.read_text(
            storage_key="../secret.txt",
            content_type="text/plain",
        )
