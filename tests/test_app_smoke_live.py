"""Optional smoke test for the Streamlit app using AppTest.

This is a light integration that attempts to execute `ui.py`. It is skipped by
default and when secrets are unavailable. It is intended to surface early
failures (e.g., immediate `st.stop`, missing secrets) in a controlled way.
"""

from __future__ import annotations

import logging
import os

import pytest
import streamlit as st

try:
    from streamlit.testing.v1 import AppTest
    app_test_available = True
except Exception:  # pragma: no cover - AppTest may not exist in older versions
    app_test_available = False


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)


def _secrets_available() -> bool:
    try:
        _ = st.secrets  # noqa: F841
    except Exception:
        return False
    return True


live_env_enabled = os.getenv("ASK_LIVE_TESTS", "0") == "1"


pytestmark = pytest.mark.live_backend


@pytest.mark.skipif(not app_test_available, reason="Streamlit AppTest not available in this environment")
@pytest.mark.skipif(not live_env_enabled, reason="Set ASK_LIVE_TESTS=1 to enable live backend tests")
@pytest.mark.skipif(not _secrets_available(), reason="Streamlit secrets not available for live tests")
def test_ui_smoke_live() -> None:
    at = AppTest.from_file("ui.py")
    at.run(timeout=90)

    # If an exception bubbles to AppTest, expose it
    if at.exception is not None:
        # AppTest.exception may not be an actual Exception instance
        try:
            raise at.exception  # type: ignore[misc]
        except TypeError:
            # Fall back to a RuntimeError with details for non-Exception payloads
            raise RuntimeError(f"Streamlit AppTest reported error: {at.exception!r}")

    # Log how many elements were rendered as a simple signal
    logger.info("UI smoke test rendered %d elements", len(at.session_state))
