from doc_reg.searcher import Searcher


class FakeEmbedder:
    def encode_query(self, query):
        return [1.0]


class FakeStore:
    def __init__(self, results_by_vault):
        self.results_by_vault = results_by_vault

    def search(self, vault_name, query_embedding, top_k=5, filter_dict=None):
        return self.results_by_vault[vault_name][:top_k]


def result(score, source, file_type="md", mtime=100, tags=""):
    return {
        "score": score,
        "content": "content",
        "metadata": {
            "source": source,
            "path": source,
            "file_type": file_type,
            "mtime": mtime,
            "tags": tags,
        },
    }


def test_search_filters_by_score_path_type_time_and_tags():
    searcher = Searcher(
        store=FakeStore(
            {
                "product-docs": [
                    result(0.9, "prd/payment.md", "md", 200, "prd,payment"),
                    result(0.2, "prd/low.md", "md", 200, "prd"),
                    result(0.8, "research/payment.pdf", "pdf", 200, "research"),
                    result(0.7, "prd/old.md", "md", 10, "prd"),
                ]
            }
        ),
        embedder=FakeEmbedder(),
        min_score=0.3,
    )

    results = searcher.search(
        query="payment",
        vault_name="product-docs",
        top_k=5,
        tags=["payment"],
        path_filter="prd/",
        file_type="md",
        since=100,
    )

    assert [item["metadata"]["source"] for item in results] == ["prd/payment.md"]


def test_search_many_sorts_across_vaults():
    searcher = Searcher(
        store=FakeStore(
            {
                "product-docs": [result(0.6, "prd/a.md")],
                "research": [result(0.9, "research/b.md")],
            }
        ),
        embedder=FakeEmbedder(),
        min_score=0.3,
    )

    results = searcher.search_many("query", ["product-docs", "research"], top_k=2)

    assert [item["metadata"]["source"] for item in results] == ["research/b.md", "prd/a.md"]
