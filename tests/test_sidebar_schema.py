import os
import sys
import types
import importlib
from typing import List

import pytest


class SidebarSpy:
    """Spy object to capture sidebar widget calls and provide deterministic returns."""

    def __init__(self):
        self.radios: list[dict] = []
        self.multiselects: list[dict] = []
        self.checkboxes: list[dict] = []
        self.captions: list[str] = []

    def radio(self, label, options, index=0, horizontal=False):
        self.radios.append({
            "label": label,
            "options": list(options),
            "index": index,
            "horizontal": horizontal,
        })
        return options[index]

    def multiselect(self, label, options, default=None, help=None):
        self.multiselects.append({
            "label": label,
            "options": list(options),
            "default": list(default or []),
            "help": help,
        })
        # Return default selection by default
        return list(default or [])

    def checkbox(self, label, value=False):
        self.checkboxes.append({"label": label, "value": value})
        return value

    def caption(self, text):
        self.captions.append(text)

    # Unused by tests but called by code
    def markdown(self, *_args, **_kwargs):
        return None


def _install_fake_streamlit(monkeypatch: pytest.MonkeyPatch, sidebar_spy: SidebarSpy):
    import streamlit as st  # type: ignore
    # Patch only sidebar methods used
    monkeypatch.setattr(st, "sidebar", sidebar_spy, raising=False)


def _install_fake_schema(monkeypatch: pytest.MonkeyPatch, scope_vals: List[str], unit_vals: List[str]):
    """Insert a fake `uscgaux` module exposing `get_allowed_values`."""
    fake = types.ModuleType("uscgaux")

    def get_allowed_values(field: str, context: dict | None = None):  # noqa: D401
        if field == "scope":
            return scope_vals
        if field == "unit":
            # Expect context {"scope": "District"}
            return unit_vals
        return []

    fake.get_allowed_values = get_allowed_values  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "uscgaux", fake)


def test_sidebar_uses_schema_when_available(monkeypatch: pytest.MonkeyPatch):
    """Verifies sidebar pulls options from the shared schema API when importable."""
    spy = SidebarSpy()
    _install_fake_streamlit(monkeypatch, spy)
    _install_fake_schema(monkeypatch, scope_vals=["National", "District"], unit_vals=["1", "7", "11N"])

    # Re-import sidebar to bind the fake schema
    if "sidebar" in sys.modules:
        del sys.modules["sidebar"]
    sidebar = importlib.import_module("sidebar")

    filters = sidebar.build_sidebar()

    # Assert radio presented expected options and included "Both"
    assert spy.radios, "No radio widget was created"
    radio_opts = spy.radios[0]["options"]
    assert "National" in radio_opts
    assert "District" in radio_opts
    assert "Both" in radio_opts, "Combined scope option 'Both' should be present"

    # When scope defaults to National, multiselect may not appear; simulate District selection
    spy.radios.clear()
    # Force District selection by re-running with index=1 using a patched radio
    def radio_force_district(label, options, index=0, horizontal=False):
        spy.radios.append({"label": label, "options": list(options), "index": 1, "horizontal": horizontal})
        return options[1]

    import streamlit as st  # type: ignore
    monkeypatch.setattr(st.sidebar, "radio", radio_force_district, raising=False)

    filters = sidebar.build_sidebar()
    # Multiselect should be shown and options come from schema
    assert spy.multiselects, "District multiselect not created for District scope"
    ms_opts = spy.multiselects[-1]["options"]
    assert ms_opts == ["1", "7", "11N"], "Units should come from schema"
    assert filters.get("scope") in ("District", "National", "Both")


def test_sidebar_fallback_without_schema(monkeypatch: pytest.MonkeyPatch):
    """Fallback is no longer supported: app requires `uscgaux` in CI/dev.

    This test is skipped to reflect the hard dependency policy.
    """
    import pytest as _pytest
    _pytest.skip("uscgaux is a hard dependency; fallback behavior is disabled.")
    spy = SidebarSpy()
    _install_fake_streamlit(monkeypatch, spy)

    # Ensure import fails by removing any cached module and making import raise
    if "uscgaux" in sys.modules:
        del sys.modules["uscgaux"]
    # Re-import sidebar fresh
    if "sidebar" in sys.modules:
        del sys.modules["sidebar"]
    sidebar = importlib.import_module("sidebar")

    _ = sidebar.build_sidebar()

    # Radio should include the three fixed scope options
    assert spy.radios, "No radio widget created"
    radio_opts = spy.radios[0]["options"]
    assert radio_opts == ["National", "District", "Both"]

    # If selecting District, multiselect options fallback to empty list
    spy.radios.clear()
    spy.multiselects.clear()

    def radio_force_district(label, options, index=0, horizontal=False):
        return "District"

    import streamlit as st  # type: ignore
    monkeypatch.setattr(st.sidebar, "radio", radio_force_district, raising=False)
    _ = sidebar.build_sidebar()

    assert spy.multiselects, "Expected multiselect when District is chosen"
    assert spy.multiselects[-1]["options"] == []


def test_catalog_filter_multi_and_both():
    """Catalog filter respects units list and Both scope composition."""
    import pandas as pd
    # Ensure project root is importable like other tests in repo
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from utils.filter import catalog_filter

    df = pd.DataFrame([
        {"pdf_id": "n1", "scope": "National", "unit": "", "status": "live"},
        {"pdf_id": "d7a", "scope": "District", "unit": "7", "status": "live"},
        {"pdf_id": "d7b", "scope": "District", "unit": "7", "status": "live"},
        {"pdf_id": "d1", "scope": "District", "unit": "1", "status": "live"},
    ])

    ids_nat = catalog_filter(df, {"scope": "National"})
    assert set(ids_nat) == {"n1"}

    ids_d7 = catalog_filter(df, {"scope": "District", "units": ["7"]})
    assert set(ids_d7) == {"d7a", "d7b"}

    ids_both = catalog_filter(df, {"scope": "Both", "units": ["7"]})
    assert set(ids_both) == {"n1", "d7a", "d7b"}
