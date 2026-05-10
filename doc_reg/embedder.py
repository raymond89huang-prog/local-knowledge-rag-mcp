from typing import List
from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str, device: str = "cpu", normalize: bool = True):
        print(f"[Embedder] Loading model: {model_name} ...")
        self.model = SentenceTransformer(model_name, device=device)
        self.normalize = normalize
        self.model_name = model_name
        print(f"[Embedder] Model loaded.")

    def encode(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def encode_query(self, query: str) -> List[float]:
        return self.encode([query])[0]
