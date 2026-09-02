from pathlib import Path

from app.ai.application.ports.document_content_reader import (
    DocumentContentReader,
)


class LocalTextDocumentContentReader(DocumentContentReader):
    def __init__(self, *, storage_root: Path) -> None:
        self._storage_root = storage_root.resolve()

    async def read_text(
        self,
        *,
        storage_key: str,
        content_type: str,
    ) -> str:
        if content_type != "text/plain":
            raise ValueError(f"Unsupported document content type: {content_type}")

        file_path = (self._storage_root / storage_key).resolve()

        if not file_path.is_relative_to(self._storage_root):
            raise ValueError("Storage key resolves outside storage root")

        return file_path.read_text(encoding="utf-8")
