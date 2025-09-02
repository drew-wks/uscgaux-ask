"""Live integration tests for backend connectors.

These tests exercise `get_backend_container` and `fetch_table_and_date`
against the real backend. They will be skipped if required secrets are not
present in `st.secrets` or if the environment is not configured for live
access.

Run with: pytest -m live_backend
Enable by setting ASK_LIVE_TESTS=1 in your environment if desired.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd
import pytest
import streamlit as st

from utils.backends_bridge import get_backend_container


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


REQUIRED_SECRET_KEYS = [
    # Keys commonly needed by the connectors; adjust as your app requires
    "OPENAI_API_KEY_ASK",
    "LANGCHAIN_API_KEY",
    # Backend-specific keys
    # If your BackendContainer relies on additional secrets, add them here
]


def _secrets_available() -> bool:
    """Return True if the minimal set of secrets appears to be available."""
    try:
        # Accessing st.secrets raises if not configured
        _ = st.secrets  # noqa: F841
    except Exception:
        return False

    for key in REQUIRED_SECRET_KEYS:
        if key not in st.secrets or not str(st.secrets.get(key)):
            logger.warning("Missing required secret: %s", key)
            return False
    return True


live_env_enabled = os.getenv("ASK_LIVE_TESTS", "0") == "1"


pytestmark = pytest.mark.live_backend


@pytest.mark.skipif(not live_env_enabled, reason="Set ASK_LIVE_TESTS=1 to enable live backend tests")
@pytest.mark.skipif(not _secrets_available(), reason="Streamlit secrets not available for live tests")
def test_get_backend_container_live() -> None:
    """Ensure `get_backend_container` returns a non-None container and key attrs.

    This test will exercise the real backend if credentials are available.
    """
    container = get_backend_container()
    assert container is not None, "BackendContainer is None"

    # Basic interface checks (duck-typing to avoid importing protocols)
    assert hasattr(container, "catalog"), "container.catalog is missing"
    logger.info("✅ Backend container acquired with catalog connector present")
