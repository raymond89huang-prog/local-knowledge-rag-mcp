from dataclasses import dataclass
from typing import List
from .document import DocumentChunk


@dataclass
class TextChunk:
    content: str
    heading: str
    path: str
    title: str
    tags: List[str]
    metadata: dict


class Chunker:
    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, doc_chunks: List[DocumentChunk]) -> List[TextChunk]:
        result: List[TextChunk] = []
        for doc_chunk in doc_chunks:
            if len(doc_chunk.content) <= self.chunk_size:
                result.append(
                    TextChunk(
                        content=doc_chunk.content,
                        heading=doc_chunk.heading,
                        path=doc_chunk.path,
                        title=doc_chunk.title,
                        tags=doc_chunk.tags,
                        metadata=doc_chunk.metadata,
                    )
                )
            else:
                sub_chunks = self._sliding_window_split(doc_chunk.content)
                for sub in sub_chunks:
                    result.append(
                        TextChunk(
                            content=sub,
                            heading=doc_chunk.heading,
                            path=doc_chunk.path,
                            title=doc_chunk.title,
                            tags=doc_chunk.tags,
                            metadata=doc_chunk.metadata,
                        )
                    )
        return result

    def _sliding_window_split(self, text: str) -> List[str]:
        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            chunk = text[start:end]
            stripped = chunk.strip()
            if stripped:
                chunks.append(stripped)
            start += self.chunk_size - self.chunk_overlap

        return chunks
