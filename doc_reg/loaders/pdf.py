from pathlib import Path
from typing import List

from doc_reg.document import DocumentChunk
from .base import DocumentLoader


class PdfLoader(DocumentLoader):
    supported_extensions = {".pdf"}

    def load(self, file_path: Path) -> List[DocumentChunk]:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        title = self._metadata_title(reader) or file_path.stem
        chunks: List[DocumentChunk] = []

        for index, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or "").strip()
            if len(text) <= 10:
                continue
            chunks.append(
                DocumentChunk(
                    content=text,
                    heading=f"Page {index}",
                    path=str(file_path),
                    title=title,
                    metadata={"file_type": "pdf", "page": index, "location": f"Page {index}"},
                )
            )

        return chunks

    @staticmethod
    def _metadata_title(reader) -> str:
        try:
            return reader.metadata.title or ""
        except Exception:
            return ""
