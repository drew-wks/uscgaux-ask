import os
import sys
import pytest
from qdrant_client.http import models
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_get_retriever_passes_filter(monkeypatch):
    dummy_filter = models.Filter(must=[])

    monkeypatch.setattr(
        st,
        "secrets",
        {
            "QDRANT_URL": "http://localhost",
            "QDRANT_API_KEY": "test",
            "OPENAI_API_KEY_ASK": "key",
        },
    )

    import utils.rag as rag

    class DummyStore:
        def __init__(self, client, collection_name, embedding):
            self.client = client
            self.collection_name = collection_name
            self.embedding = embedding

        def as_retriever(self, search_type, search_kwargs):
            self.search_type = search_type
            self.search_kwargs = search_kwargs
            return self

    monkeypatch.setattr(rag, "QdrantClient", lambda *a, **kw: "client")
    monkeypatch.setattr(rag, "OpenAIEmbeddings", lambda model: "embedding")
    monkeypatch.setattr(rag, "QdrantVectorStore", DummyStore)

    retriever = rag.get_retriever(dummy_filter)
    assert isinstance(retriever, DummyStore)
    assert retriever.search_kwargs["filter"] is dummy_filter
    assert retriever.search_type == rag.CONFIG["ASK_search_type"]
