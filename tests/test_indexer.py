from doc_reg.chunker import Chunker
from doc_reg.config import VaultConfig
from doc_reg.indexer import Indexer


class FakeEmbedder:
    def encode(self, documents):
        return [[float(index)] for index, _ in enumerate(documents)]


class FakeStore:
    def __init__(self):
        self.deleted_sources = []
        self.upserts = []

    def delete_by_sources(self, vault_name, sources):
        self.deleted_sources.append((vault_name, list(sources)))

    def upsert_chunks(self, vault_name, ids, documents, embeddings, metadatas):
        self.upserts.append(
            {
                "vault_name": vault_name,
                "ids": ids,
                "documents": documents,
                "embeddings": embeddings,
                "metadatas": metadatas,
            }
        )


def test_indexer_cleans_existing_source_and_writes_citation_metadata(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    doc_path = vault_path / "prd.md"
    doc_path.write_text("# Scope\nMember retention policy and renewal plan.", encoding="utf-8")

    store = FakeStore()
    indexer = Indexer(
        vault_config=VaultConfig(name="product-docs", path=str(vault_path), include=["**/*.md"]),
        embedder=FakeEmbedder(),
        store=store,
        chunker=Chunker(chunk_size=200, chunk_overlap=20),
        checkpoint_dir=str(tmp_path / "checkpoints"),
    )

    indexer.index()

    assert store.deleted_sources == [("product-docs", ["prd.md"])]
    assert len(store.upserts) == 1
    metadata = store.upserts[0]["metadatas"][0]
    assert metadata["vault"] == "product-docs"
    assert metadata["source"] == "prd.md"
    assert metadata["file_type"] == "md"
    assert metadata["citation"] == "prd.md#Scope"


def test_indexer_deletes_removed_file_from_store_and_checkpoint(tmp_path):
    vault_path = tmp_path / "vault"
    vault_path.mkdir()
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    checkpoint = checkpoint_dir / "product-docs.json"
    checkpoint.write_text(
        '{"files": {"removed.md": {"hash": "old", "mtime": 1, "chunks": 1}}}',
        encoding="utf-8",
    )
    store = FakeStore()
    indexer = Indexer(
        vault_config=VaultConfig(name="product-docs", path=str(vault_path), include=["**/*.md"]),
        embedder=FakeEmbedder(),
        store=store,
        chunker=Chunker(),
        checkpoint_dir=str(checkpoint_dir),
    )

    indexer.index()

    assert store.deleted_sources == [("product-docs", ["removed.md"])]
    assert '"removed.md"' not in checkpoint.read_text(encoding="utf-8")
