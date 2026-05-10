import hashlib
import json
from pathlib import Path
from typing import Dict, List, Set

from .chunker import Chunker
from .config import VaultConfig
from .embedder import Embedder
from .loaders import LoaderRegistry
from .store import VectorStore


class CheckpointManager:
    def __init__(self, checkpoint_dir: str):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def get_checkpoint_path(self, vault_name: str) -> Path:
        return self.checkpoint_dir / f"{vault_name}.json"

    def load(self, vault_name: str) -> Dict:
        path = self.get_checkpoint_path(vault_name)
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"files": {}}

    def save(self, vault_name: str, data: Dict):
        path = self.get_checkpoint_path(vault_name)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class Indexer:
    def __init__(
        self,
        vault_config: VaultConfig,
        embedder: Embedder,
        store: VectorStore,
        chunker: Chunker,
        checkpoint_dir: str,
        loader_registry: LoaderRegistry | None = None,
    ):
        self.vault = vault_config
        self.embedder = embedder
        self.store = store
        self.chunker = chunker
        self.loader_registry = loader_registry or LoaderRegistry()
        self.checkpoint_mgr = CheckpointManager(checkpoint_dir)

    def index(self, force: bool = False):
        vault_path = self.vault.resolved_path()
        if not vault_path.exists():
            raise FileNotFoundError(f"Vault path does not exist: {vault_path}")

        checkpoint = self.checkpoint_mgr.load(self.vault.name)
        current_files = self._scan_files(vault_path)
        current_keys: Set[str] = set()
        to_index: List[Path] = []
        to_delete: List[str] = []

        for file_path in current_files:
            file_key = self._source_key(file_path, vault_path)
            current_keys.add(file_key)

            try:
                stat = file_path.stat()
                file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
                old = checkpoint["files"].get(file_key)
                if force or not old or old.get("hash") != file_hash or old.get("mtime") != stat.st_mtime:
                    to_index.append(file_path)
            except Exception as e:
                print(f"  [WARN] {file_key}: stat/hash error: {e}")

        for old_key in list(checkpoint["files"].keys()):
            if old_key not in current_keys:
                to_delete.append(old_key)

        print(f"[Indexer] Vault: {self.vault.name}")
        print(f"[Indexer] Path: {vault_path}")
        print(f"[Indexer] Total files: {len(current_files)}")
        print(f"[Indexer] To index/update: {len(to_index)}")
        print(f"[Indexer] To delete: {len(to_delete)}")

        if to_delete:
            self.store.delete_by_sources(self.vault.name, to_delete)
            for key in to_delete:
                checkpoint["files"].pop(key, None)

        for file_path in to_index:
            self._index_file(file_path, vault_path, checkpoint)

        self.checkpoint_mgr.save(self.vault.name, checkpoint)
        print("[Indexer] Done.")

    def _scan_files(self, vault_path: Path) -> List[Path]:
        files: Set[Path] = set()
        supported_extensions = self.loader_registry.supported_extensions()

        for pattern in self.vault.include:
            for file_path in vault_path.rglob(pattern):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.add(file_path.resolve())

        for pattern in self.vault.exclude:
            for file_path in vault_path.rglob(pattern):
                files.discard(file_path.resolve())

        return sorted(files)

    def _index_file(self, file_path: Path, vault_path: Path, checkpoint: Dict):
        file_key = self._source_key(file_path, vault_path)
        try:
            doc_chunks = self.loader_registry.load(file_path)
            chunks = self.chunker.chunk_document(doc_chunks)

            self.store.delete_by_sources(self.vault.name, [file_key])

            if not chunks:
                checkpoint["files"].pop(file_key, None)
                print(f"  [SKIP] {file_key} (no content)")
                return

            stat = file_path.stat()
            ids = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_key}::chunk_{i}"
                metadata = self._metadata_for_chunk(chunk.metadata)
                metadata.update(
                    {
                        "vault": self.vault.name,
                        "path": str(file_path),
                        "source": file_key,
                        "title": chunk.title,
                        "heading": chunk.heading,
                        "tags": ",".join(chunk.tags),
                        "mtime": stat.st_mtime,
                        "file_type": metadata.get("file_type") or file_path.suffix.lower().lstrip("."),
                        "citation": self._citation(file_key, metadata, chunk.heading),
                    }
                )
                ids.append(chunk_id)
                documents.append(chunk.content)
                metadatas.append(metadata)

            embeddings = self.embedder.encode(documents)
            self.store.upsert_chunks(
                vault_name=self.vault.name,
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            checkpoint["files"][file_key] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": hashlib.md5(file_path.read_bytes()).hexdigest(),
                "chunks": len(chunks),
                "file_type": file_path.suffix.lower().lstrip("."),
            }
            print(f"  [OK] {file_key} ({len(chunks)} chunks)")
        except Exception as e:
            print(f"  [ERR] {file_key}: {e}")

    @staticmethod
    def _source_key(file_path: Path, vault_path: Path) -> str:
        return str(file_path.relative_to(vault_path)).replace("\\", "/")

    @staticmethod
    def _metadata_for_chunk(metadata: Dict) -> Dict:
        clean: Dict = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif isinstance(value, list):
                clean[key] = ", ".join(str(item) for item in value)
            else:
                clean[key] = str(value)
        return clean

    @staticmethod
    def _citation(source: str, metadata: Dict, heading: str) -> str:
        file_type = metadata.get("file_type", "")
        if file_type == "pdf" and metadata.get("page"):
            return f"{source}#page={metadata['page']}"
        if file_type == "xlsx" and metadata.get("sheet"):
            return f"{source}#{metadata['sheet']}!rows={metadata.get('row_start')}-{metadata.get('row_end')}"
        if file_type == "csv" and metadata.get("row_start"):
            return f"{source}#rows={metadata.get('row_start')}-{metadata.get('row_end')}"
        if heading:
            return f"{source}#{heading}"
        return source
