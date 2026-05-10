from typing import Dict, List, Optional

from .embedder import Embedder
from .store import VectorStore


class Searcher:
    def __init__(self, store: VectorStore, embedder: Embedder, min_score: float = 0.3):
        self.store = store
        self.embedder = embedder
        self.min_score = min_score

    def search(
        self,
        query: str,
        vault_name: str,
        top_k: int = 5,
        tags: Optional[List[str]] = None,
        path_filter: Optional[str] = None,
        file_type: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> List[Dict]:
        query_embedding = self.embedder.encode_query(query)
        results = self.store.search(
            vault_name=vault_name,
            query_embedding=query_embedding,
            top_k=top_k * 5,
        )

        filtered = []
        for result in results:
            metadata = result.get("metadata", {})
            if result["score"] < self.min_score:
                continue
            if path_filter and path_filter not in metadata.get("source", "") and path_filter not in metadata.get("path", ""):
                continue
            if file_type and metadata.get("file_type") != file_type.lstrip(".").lower():
                continue
            if since and float(metadata.get("mtime", 0)) < since:
                continue
            if until and float(metadata.get("mtime", 0)) > until:
                continue
            if tags:
                metadata_tags = {tag.strip() for tag in metadata.get("tags", "").split(",") if tag.strip()}
                if not set(tags).intersection(metadata_tags):
                    continue

            filtered.append(result)
            if len(filtered) >= top_k:
                break

        return filtered

    def search_many(
        self,
        query: str,
        vault_names: List[str],
        top_k: int = 5,
        path_filter: Optional[str] = None,
        file_type: Optional[str] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> List[Dict]:
        all_results: List[Dict] = []
        per_vault = max(top_k, 3)
        for vault_name in vault_names:
            all_results.extend(
                self.search(
                    query=query,
                    vault_name=vault_name,
                    top_k=per_vault,
                    path_filter=path_filter,
                    file_type=file_type,
                    since=since,
                    until=until,
                )
            )
        all_results.sort(key=lambda item: item["score"], reverse=True)
        return all_results[:top_k]
