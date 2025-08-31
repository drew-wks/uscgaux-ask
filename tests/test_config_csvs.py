import os
import sys
import pytest
import streamlit as st


def _prime_streamlit_secrets(monkeypatch):
    """Provide the minimal secrets expected by utils.rag at import time."""
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


def test_get_retrieval_context_csv_loads_acronyms(monkeypatch):
    _prime_streamlit_secrets(monkeypatch)
    import utils.rag as rag

    data = rag.get_retrieval_context_csv(rag.ACRONYMS_PATH)
    # Basic shape and a known mapping from the repo CSV
    assert isinstance(data, dict)
    assert len(data) > 0
    assert "AUXSCOUT" in data
    assert "SEA SCOUT" in str(data["AUXSCOUT"]).upper()


def test_get_retrieval_context_csv_loads_terms(monkeypatch):
    _prime_streamlit_secrets(monkeypatch)
    import utils.rag as rag

    data = rag.get_retrieval_context_csv(rag.TERMS_PATH)
    assert isinstance(data, dict)
    assert len(data) > 0
    # Expect a known term present in config/terms.csv
    assert "Boat crew" in data or "Boat crew" in map(str, data.keys())


def test_get_retrieval_context_csv_requires_two_columns(tmp_path, monkeypatch):
    _prime_streamlit_secrets(monkeypatch)
    import utils.rag as rag

    bad = tmp_path / "bad.csv"
    bad.write_text("only_one_col\nvalue\n", encoding="utf-8")
    with pytest.raises(ValueError):
        rag.get_retrieval_context_csv(str(bad))


def test_enrich_question_expands_acronyms_and_terms(monkeypatch):
    _prime_streamlit_secrets(monkeypatch)
    import utils.rag as rag

    question = "Tell me about AUXSCOUT and Boat crew."
    enriched = rag.enrich_question(question, rag.ACRONYMS_PATH, rag.TERMS_PATH)

    # Should expand the acronym and append the term explanation
    assert "AUXILIARY" in enriched.upper()  # expanded AUXSCOUT
    assert "BOAT CREW" in enriched.upper()
    assert ")" in enriched  # implication appended in parentheses

