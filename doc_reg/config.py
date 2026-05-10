import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EmbeddingConfig:
    model_name: str = "BAAI/bge-small-zh-v1.5"
    device: str = "cpu"
    normalize: bool = True


@dataclass
class ChunkingConfig:
    chunk_size: int = 400
    chunk_overlap: int = 50
    respect_headings: bool = True


@dataclass
class VaultConfig:
    name: str = ""
    path: str = ""
    description: str = ""
    include: List[str] = field(default_factory=lambda: ["**/*.md"])
    exclude: List[str] = field(default_factory=list)

    def resolved_path(self) -> Path:
        expanded = os.path.expandvars(os.path.expanduser(self.path))
        return Path(expanded).resolve()


@dataclass
class SearchConfig:
    default_top_k: int = 5
    min_score: float = 0.3


@dataclass
class AppConfig:
    embedding: EmbeddingConfig
    chunking: ChunkingConfig
    vaults: Dict[str, VaultConfig]
    search: SearchConfig

    @classmethod
    def from_yaml(cls, path: str) -> "AppConfig":
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        embedding = EmbeddingConfig(**data.get("embedding", {}))
        chunking = ChunkingConfig(**data.get("chunking", {}))
        search = SearchConfig(**data.get("search", {}))

        vaults = {}
        for name, vdata in data.get("vaults", {}).items():
            vaults[name] = VaultConfig(name=name, **vdata)

        return cls(
            embedding=embedding,
            chunking=chunking,
            vaults=vaults,
            search=search,
        )

    def get_vault(self, name: Optional[str] = None) -> VaultConfig:
        if name:
            if name not in self.vaults:
                raise ValueError(f"Vault '{name}' not found in config. Available: {list(self.vaults.keys())}")
            return self.vaults[name]
        if not self.vaults:
            raise ValueError("No vaults configured")
        return next(iter(self.vaults.values()))

    def list_vaults(self) -> List[VaultConfig]:
        return list(self.vaults.values())
