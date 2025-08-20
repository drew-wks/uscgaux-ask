import json
from pathlib import Path

import pytest
from google.oauth2.service_account import Credentials
import tomllib


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
    if isinstance(creds_data, str):
        creds_file = Path(creds_data)
        assert creds_file.exists(), "Credential path specified does not exist"
        with creds_file.open() as cf:
            creds_info = json.load(cf)
    else:
        creds_info = creds_data

    # Attempt to construct Credentials object to verify structure
    Credentials.from_service_account_info(creds_info)

    # Basic required fields
    assert creds_info.get("client_email"), "client_email missing in credentials"
    assert creds_info.get("private_key"), "private_key missing in credentials"
