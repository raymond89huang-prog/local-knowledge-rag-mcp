from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from doc_rag.document import DocumentChunk


class DocumentLoader(ABC):
    supported_extensions: set[str] = set()

    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in self.supported_extensions

    @abstractmethod
    def load(self, file_path: Path) -> List[DocumentChunk]:
        raise NotImplementedError

