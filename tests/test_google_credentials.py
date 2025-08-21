import json
from pathlib import Path
import tomllib
import pytest

def test_gcp_service_account_credentials_present_and_valid():
    """Ensure Google service account credentials exist and can be parsed."""
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        pytest.skip(".streamlit/secrets.toml not found")

    with secrets_path.open("rb") as f:
        secrets = tomllib.load(f)

    key = "GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP"
    assert key in secrets, f"Missing '{key}' in secrets.toml"

    creds_data = secrets[key]

    # Accept 3 shapes: dict, inline JSON string, or path string
    if isinstance(creds_data, dict):
        creds = creds_data

    elif isinstance(creds_data, str):
        s = creds_data.strip()
        if s.startswith("{"):
            # inline JSON in secrets.toml
            try:
                creds = json.loads(s)
            except json.JSONDecodeError as e:
                pytest.fail(f"Inline JSON credentials not valid JSON: {e}")
        else:
            # path to a JSON file
            creds_file = Path(s).expanduser()
            assert creds_file.exists(), "Credential path specified does not exist"
            creds = json.loads(creds_file.read_text())

    else:
        pytest.fail(f"Unsupported credential format: {type(creds_data)}")

    # Minimal sanity checks on the loaded creds
    for required in ("type", "client_email", "private_key"):
        assert required in creds, f"Missing '{required}' in credentials JSON"
    assert creds.get("type") == "service_account"