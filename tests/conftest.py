import chromadb
import pytest

import rag

KEYWORDS = ["password", "reset", "plan", "price", "trial", "api", "request", "trash", "deleted",
            "support", "hours", "invoice", "refund", "mobile", "slack", "stripe", "2fa", "standard"]


class FakeEmbedding(chromadb.EmbeddingFunction):
    def __init__(self):
        pass

    def __call__(self, input):
        vectors = []
        for text in input:
            lower = text.lower()
            vector = [float(lower.count(word)) for word in KEYWORDS] + [0.1]
            length = sum(value * value for value in vector) ** 0.5
            vectors.append([value / length for value in vector])
        return vectors

    @staticmethod
    def name():
        return "fake-keywords"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return FakeEmbedding()


@pytest.fixture(autouse=True)
def fake_vector_store(tmp_path, monkeypatch):
    monkeypatch.setattr(rag, "CHROMA_FOLDER", tmp_path / "chroma")
    monkeypatch.setattr(rag, "embedding_function", FakeEmbedding())
