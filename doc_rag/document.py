from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DocumentChunk:
    content: str
    heading: str
    path: str
    title: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
