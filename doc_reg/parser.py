from pathlib import Path
from typing import List

from .document import DocumentChunk
from .loaders.markdown import MarkdownLoader


class MarkdownParser:
    def __init__(self):
        self.loader = MarkdownLoader()

    def parse_file(self, file_path: Path) -> List[DocumentChunk]:
        return self.loader.load(file_path)
