import os
import time
from typing import Any
import pytest
import streamlit as st

# Ensure AppTest is always bound for static analysis
try:
    from streamlit.testing.v1 import AppTest  # type: ignore[import-not-found]
    app_test_available = True
except Exception:
    AppTest = None  # type: ignore[assignment]
    app_test_available = False

# requries streamlit version >=1.18


@pytest.mark.skipif(not app_test_available, reason="Streamlit AppTest not available in this environment")
def test_ui():
    """Test case for the Streamlit user interface I/O using streamlit testing framework AppTest.

    This test performs the following steps:
    1. Initializes the Streamlit app using `AppTest.from_file` with the `ui.py` script.
    2. Runs the app and verifies it starts without exceptions.
    3. Simulates user input by entering a question into the text input field to test
       the app's response to a typical query, "How do I stay current in boat crew?"
    4. Checks for any exceptions during user input simulation and verifies that 
       the app processed the input without errors.
    5. Retrieves the app's response and asserts that it contains the keyword "Response,"
       indicating that the app provided feedback to the query in the expected format.
    6. Returns "tests/test_ui.py::test_ui PASSED"  in the console if the test passes.

    Passing this test confirms:
    - The app can load and run without errors.
    - User input can be entered and processed.
    - The app generates an output response in the expected format.

    Raises:
        AssertionError: If any of the steps result in an unexpected outcome or if
                        exceptions occur during app loading or input processing.
    """
    # Only run this UI test when explicitly enabled and dependencies are present
    if os.getenv("ASK_LIVE_TESTS", "0") != "1":
        pytest.skip("Set ASK_LIVE_TESTS=1 to enable UI AppTest")

    # Require a minimal set of secrets to avoid runtime errors
    required = ["LANGCHAIN_API_KEY", "OPENAI_API_KEY_ASK"]
    try:
        missing = [k for k in required if not str(st.secrets.get(k, "")).strip()]
        if missing:
            pytest.skip(f"Missing secrets for UI test: {', '.join(missing)}")
    except Exception:
        pytest.skip("No Streamlit secrets found")

    # Ensure external dependency is available
    pytest.importorskip("uscgaux", reason="uscgaux package not installed. Install via requirements.txt")

    print("Starting AppTest")
    at = AppTest.from_file("ui.py", default_timeout=5)
    print("Running AppTest")
    at.run()
    
    # Confirm the available text inputs and use the correct one
    print("Available text inputs:", at.text_input)
    at.text_input[0].input("How do I stay current in boat crew?").run(timeout=10)
    
    assert not at.exception, f"An exception occurred: {at.exception}"
    print("No exceptions occurred after mocking user input")
    
    first_response = at.info[0].value
    assert "Response" in first_response  # Check if the response is shown in the info box
    print("Test completed successfully")
    
