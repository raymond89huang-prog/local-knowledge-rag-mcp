import re
from pathlib import Path
from typing import Any, Dict, List

import frontmatter

from doc_reg.document import DocumentChunk
from .base import DocumentLoader


class MarkdownLoader(DocumentLoader):
    supported_extensions = {".md", ".markdown"}

    def __init__(self):
        self.wiki_link_pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
        self.heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

    def load(self, file_path: Path) -> List[DocumentChunk]:
        content = file_path.read_text(encoding="utf-8")
        post = frontmatter.loads(content)
        metadata = dict(post.metadata)
        body = post.content

        title = str(metadata.get("title") or file_path.stem)
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []

        metadata["wiki_links"] = self.wiki_link_pattern.findall(body)
        metadata["file_type"] = file_path.suffix.lower().lstrip(".")

        return self._split_by_headings(body, file_path, title, tags, metadata)

    def _split_by_headings(
        self,
        body: str,
        file_path: Path,
        title: str,
        tags: List[str],
        metadata: Dict[str, Any],
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        current_heading = title
        current_content: List[str] = []

        for line in body.splitlines():
            heading_match = self.heading_pattern.match(line)
            if heading_match:
                self._append_chunk(chunks, current_content, current_heading, file_path, title, tags, metadata)
                current_heading = heading_match.group(2).strip()
                current_content = [line]
            else:
                current_content.append(line)

        self._append_chunk(chunks, current_content, current_heading, file_path, title, tags, metadata)
        return chunks

    @staticmethod
    def _append_chunk(
        chunks: List[DocumentChunk],
        lines: List[str],
        heading: str,
        file_path: Path,
        title: str,
        tags: List[str],
        metadata: Dict[str, Any],
    ):
        chunk_text = "\n".join(lines).strip()
        if len(chunk_text) <= 10:
            return
        chunks.append(
            DocumentChunk(
                content=chunk_text,
                heading=heading,
                path=str(file_path),
                title=title,
                tags=tags,
                metadata=dict(metadata),
            )
        )
