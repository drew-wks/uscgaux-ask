import os
import sys
import pytest
from qdrant_client.http import models
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_get_retriever_passes_filter(monkeypatch):
    """get_retriever should pass the provided filter to the vectorstore retriever."""
    dummy_filter = models.Filter(must=[])

    # Provide minimal secrets expected by utils.rag
    monkeypatch.setattr(
        st,
        "secrets",
        {
            "QDRANT_URL": "http://localhost",
            "QDRANT_API_KEY": "test",
            "OPENAI_API_KEY_ASK": "key",
        },
        raising=False,
    )

    import utils.rag as rag

    # Create a fake vectorstore retriever that records kwargs
    class DummyRetriever:
        def __init__(self):
            self.search_type = None
            self.search_kwargs = None

        def as_retriever(self, search_type, search_kwargs):
            self.search_type = search_type
            self.search_kwargs = search_kwargs
            return self

    class DummyVectorStore:
        def __init__(self):
            self.retriever = DummyRetriever()

        def as_retriever(self, search_type, search_kwargs):
            return self.retriever.as_retriever(search_type, search_kwargs)

    class DummyConnector:
        def get_langchain_vectorstore(self):
            return DummyVectorStore()

    # Patch rag.get_vectordb_connector to return our dummy connector
    monkeypatch.setattr(rag, "get_vectordb_connector", lambda: DummyConnector())

    retriever = rag.get_retriever(dummy_filter)
    # Our get_retriever returns the retriever from the vectorstore
    assert isinstance(retriever, DummyRetriever)
    assert retriever.search_kwargs["filter"] is dummy_filter
    assert retriever.search_type == rag.CONFIG["ASK_search_type"]
