from pathlib import Path
from typing import List

from doc_reg.document import DocumentChunk
from .base import DocumentLoader


class TextLoader(DocumentLoader):
    supported_extensions = {".txt"}

    def load(self, file_path: Path) -> List[DocumentChunk]:
        content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            return []
        return [
            DocumentChunk(
                content=content,
                heading=file_path.stem,
                path=str(file_path),
                title=file_path.stem,
                metadata={"file_type": "txt"},
            )
        ]
