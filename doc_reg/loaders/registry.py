from pathlib import Path
from typing import List

from doc_reg.document import DocumentChunk
from .base import DocumentLoader
from .docx import DocxLoader
from .markdown import MarkdownLoader
from .pdf import PdfLoader
from .spreadsheet import SpreadsheetLoader
from .text import TextLoader


class LoaderRegistry:
    def __init__(self, loaders: List[DocumentLoader] | None = None):
        self.loaders = loaders or [
            MarkdownLoader(),
            TextLoader(),
            DocxLoader(),
            PdfLoader(),
            SpreadsheetLoader(),
        ]

    def supported_extensions(self) -> set[str]:
        extensions: set[str] = set()
        for loader in self.loaders:
            extensions.update(loader.supported_extensions)
        return extensions

    def load(self, file_path: Path) -> List[DocumentChunk]:
        for loader in self.loaders:
            if loader.supports(file_path):
                return loader.load(file_path)
        raise ValueError(f"Unsupported file type: {file_path.suffix}")
