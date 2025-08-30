from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Tuple

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource as DriveClient, build

# Optional imports from the uscgaux package (installed via requirements.txt).
# These are used for provider-agnostic access to the catalog via connectors.
try:
    from uscgaux.config.loader import load_config_by_context
    from uscgaux.backends import init_connectors
except Exception:  # pragma: no cover - allow runtime environments without the package to import
    load_config_by_context = None  # type: ignore[assignment]
    init_connectors = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)



def get_gcp_credentials() -> Credentials:
    """Build Google credentials from a flattened JSON in Streamlit secrets.

    Returns
    -------
    google.oauth2.service_account.Credentials
        Service account credentials for Google APIs.
    """
    creds_json = st.secrets["GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP"]
    if not creds_json:
        msg = "Missing GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP in environment."
        logger.error(msg)
        raise EnvironmentError(msg)
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict)
        return creds
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load GCP credentials from environment")
        raise ValueError(f"Failed to load GCP credentials from environment: {exc}") from exc
    
    
def init_drive_client(creds: Credentials) -> DriveClient:
    """Initialize a Google Drive client with the given credentials.

    Parameters
    ----------
    creds : Credentials
        Google service account or user credentials.

    Returns
    -------
    googleapiclient.discovery.Resource
        Authorized client for Google Drive v3 API.
    """
    scoped_creds = creds.with_scopes(["https://www.googleapis.com/auth/drive"])
    client = build("drive", "v3", credentials=scoped_creds)
    logger.info("Google Drive client initialized with scoped credentials")
    return client

    
def init_sheets_client(creds: Credentials) -> gspread.client.Client:
    """Initialize a Google Sheets client with the given credentials.

    Parameters
    ----------
    creds : Credentials
        Google service account or user credentials.

    Returns
    -------
    gspread.client.Client
        Authorized gspread client for Google Sheets.
    """
    scoped_creds = creds.with_scopes(
        [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    client = gspread.authorize(scoped_creds)
    logger.info("Google Sheets client initialized with scoped credentials")
    return client


# --- Backend container (uscgaux) -------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_backend_container() -> Any:
    """Return a cached BackendContainer initialized from the active context.

    Uses the uscgaux configuration loader and backend initializer to build a
    provider-agnostic set of connectors. The result is cached for reuse.

    Returns
    -------
    Any
        A BackendContainer from ``uscgaux.backends`` (type left as Any to avoid
        import-time tight coupling during local tooling or tests).
    """
    if load_config_by_context is None or init_connectors is None:
        logger.warning(
            "uscgaux package not available; backend container cannot be initialized"
        )
        return None

    cfg = load_config_by_context()
    container = init_connectors(cfg)
    logger.info("Initialized BackendContainer via uscgaux connectors")
    return container


@st.cache_data(show_spinner=False)
def load_table_and_date() -> Tuple[pd.DataFrame, str]:
    """Return the catalog DataFrame and its last modified timestamp.

    This helper uses the uscgaux provider adapter (CatalogConnector) only. No
    direct Google Sheets/Drive fallback is performed.

    Returns
    -------
    tuple[pandas.DataFrame, str]
        A DataFrame of the catalog (filtered to status=live when possible) and
        an ISO-formatted last modified time (UTC). Empty values on failure.
    """
    try:
        container = get_backend_container()
        if not container or getattr(container, "catalog", None) is None:
            logger.error("BackendContainer or CatalogConnector unavailable")
            return pd.DataFrame(), ""

        catalog = container.catalog  # type: ignore[attr-defined]

        # Fetch the catalog DataFrame strictly via connector API/attributes
        df: pd.DataFrame | None = None
        for method_name in ("get_catalog", "load_catalog", "get_catalog_df"):
            method = getattr(catalog, method_name, None)
            if callable(method):
                candidate = method()  # type: ignore[call-arg]
                if isinstance(candidate, pd.DataFrame):
                    df = candidate
                    break

        if df is None:
            maybe_df = getattr(catalog, "catalog_df", None)
            if isinstance(maybe_df, pd.DataFrame):
                df = maybe_df

        # Get modified time via adapter API if available
        modified_time = ""
        get_mtime = getattr(catalog, "get_catalog_modified_time", None)
        if callable(get_mtime):
            mt = get_mtime()
            if isinstance(mt, str):
                modified_time = mt
            elif isinstance(mt, datetime):
                modified_time = mt.strftime("%Y-%m-%dT%H:%M:%SZ")

        if df is None:
            logger.error("CatalogConnector did not return a DataFrame")
            return pd.DataFrame(), modified_time

        if "status" in df.columns:
            live_mask = df["status"].astype(str).str.strip().str.lower() == "live"
            df = df[live_mask]
        logger.info("Loaded catalog via uscgaux provider adapter (no fallback)")
        return df, modified_time
    except Exception:  # noqa: BLE001
        logger.exception("Failed to load catalog via provider adapter")
        return pd.DataFrame(), ""
