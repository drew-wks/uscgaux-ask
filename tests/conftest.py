import os
import sys


# Ensure project root is importable for all tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if not sys.path or sys.path[0] != ROOT:
    # Ensure project root takes precedence over site-packages 'utils'
    if ROOT in sys.path:
        sys.path.remove(ROOT)
    sys.path.insert(0, ROOT)


# Provide default Streamlit secrets to avoid import-time KeyError in modules
try:
    import streamlit as st  # type: ignore

    class DummySecrets(dict):
        pass

    default_secrets = DummySecrets(
        {
            "QDRANT_URL": "",
            "QDRANT_API_KEY": "",
            "OPENAI_API_KEY_ASK": "",
            "LANGCHAIN_API_KEY": "",
            "CATALOG_ID": "",
            "ENRICHMENT_SPREADSHEET_ID": "",
        }
    )

    # Only set if not already provided by the environment/tests
    if not hasattr(st, "secrets") or not isinstance(st.secrets, dict):
        st.secrets = default_secrets  # type: ignore[assignment]
except Exception:
    # If streamlit is unavailable for any reason during collection, ignore
    pass
