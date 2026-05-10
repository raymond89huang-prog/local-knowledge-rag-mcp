from pathlib import Path
from typing import List

from doc_reg.document import DocumentChunk
from .base import DocumentLoader


class DocxLoader(DocumentLoader):
    supported_extensions = {".docx"}

    def load(self, file_path: Path) -> List[DocumentChunk]:
        from docx import Document

        document = Document(str(file_path))
        title = self._core_title(document) or file_path.stem
        chunks: List[DocumentChunk] = []
        current_heading = title
        current_lines: List[str] = []

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            style = paragraph.style.name if paragraph.style else ""
            if style.lower().startswith("heading"):
                self._append_chunk(chunks, current_lines, current_heading, file_path, title)
                current_heading = text
                current_lines = [text]
            else:
                current_lines.append(text)

        self._append_chunk(chunks, current_lines, current_heading, file_path, title)
        return chunks

    @staticmethod
    def _core_title(document) -> str:
        try:
            return document.core_properties.title or ""
        except Exception:
            return ""

    @staticmethod
    def _append_chunk(
        chunks: List[DocumentChunk],
        lines: List[str],
        heading: str,
        file_path: Path,
        title: str,
    ):
        content = "\n".join(lines).strip()
        if len(content) <= 10:
            return
        chunks.append(
            DocumentChunk(
                content=content,
                heading=heading,
                path=str(file_path),
                title=title,
                metadata={"file_type": "docx", "location": heading},
            )
        )
