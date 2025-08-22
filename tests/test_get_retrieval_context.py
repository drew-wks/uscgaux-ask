import os
import sys
import streamlit as st


class DummySecrets(dict):
    pass


st.secrets = DummySecrets(
    {
        "QDRANT_URL": "",
        "QDRANT_API_KEY": "",
        "OPENAI_API_KEY_ASK": "",
        "CATALOG_ID": "",
        "ENRICHMENT_SPREADSHEET_ID": "",
    }
)

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils import rag


def test_get_retrieval_context_builds_dict(monkeypatch):
    class FakeWorksheet:
        def __init__(self, title, values):
            self.title = title
            self._values = values

        def get_all_values(self):
            return self._values

    class FakeWorkbook:
        def __init__(self, worksheets):
            self._worksheets = worksheets

        def worksheets(self):
            return self._worksheets

    fake_workbook = FakeWorkbook([
        FakeWorksheet("acronyms", [["short", "long"], ["USCG", "United States Coast Guard"]]),
        FakeWorksheet("terms", [["term", "explanation"], ["Aux", "Auxiliary"]]),
    ])

    def mock_get_gcp_credentials():
        return object()

    class FakeSheetsClient:
        def open_by_key(self, key):
            assert key == "spreadsheet123"
            return fake_workbook

    def mock_init_sheets_client(creds):
        return FakeSheetsClient()

    monkeypatch.setattr(rag, "get_gcp_credentials", mock_get_gcp_credentials)
    monkeypatch.setattr(rag, "init_sheets_client", mock_init_sheets_client)

    context = rag.get_retrieval_context("spreadsheet123")
    assert context["acronyms"]["USCG"] == "United States Coast Guard"
    assert context["terms"]["Aux"] == "Auxiliary"


def test_enrich_question_passes_spreadsheet_id(monkeypatch):
    called = {}

    def fake_get_retrieval_context(spreadsheet_id):
        called["id"] = spreadsheet_id
        return {"acronyms": {}, "terms": {}}

    monkeypatch.setattr(rag, "get_retrieval_context", fake_get_retrieval_context)

    rag.enrich_question("question", spreadsheet_id="sheet42")
    assert called["id"] == "sheet42"
