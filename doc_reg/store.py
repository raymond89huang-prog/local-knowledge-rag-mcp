from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings


class VectorStore:
    def __init__(self, persist_directory: str):
        Path(persist_directory).parent.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_directory,
                anonymized_telemetry=False,
                is_persistent=True,
            )
        )

    def get_or_create_collection(self, vault_name: str):
        return self.client.get_or_create_collection(
            name=vault_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        vault_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict],
    ):
        if not ids:
            return
        collection = self.get_or_create_collection(vault_name)
        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_by_paths(self, vault_name: str, paths: List[str]):
        self._delete_by_metadata(vault_name, "path", paths)

    def delete_by_sources(self, vault_name: str, sources: List[str]):
        self._delete_by_metadata(vault_name, "source", sources)

    def _delete_by_metadata(self, vault_name: str, field: str, values: List[str]):
        if not values:
            return
        collection = self.get_or_create_collection(vault_name)
        batch_size = 100
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            try:
                result = collection.get(where={field: {"$in": batch}})
                ids = result.get("ids", []) if result else []
                if ids:
                    collection.delete(ids=ids)
            except Exception as e:
                print(f"[Store] Warning: failed to delete {field} batch: {e}")

    def search(
        self,
        vault_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict]:
        collection = self.get_or_create_collection(vault_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_dict,
            include=["documents", "metadatas", "distances"],
        )

        output: List[Dict] = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                distance = results["distances"][0][i]
                output.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": distance,
                        "score": 1.0 - distance,
                    }
                )
        return output

    def get_stats(self, vault_name: str) -> Dict:
        collection = self.get_or_create_collection(vault_name)
        return {"chunks": collection.count()}
