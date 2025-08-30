from __future__ import annotations

import json
import logging
from typing import Any, Tuple, Optional

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import Resource as DriveClient, build


from uscgaux import stu
from uscgaux.config.loader import load_config_by_context
from uscgaux.backends import BackendContainer


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

@st.cache_resource(show_spinner=True)
def get_backend_container() -> BackendContainer:
    """Return a cached BackendContainer

    Loads the active configuration via ``load_config_by_context()`` and passes
    it into ``stu.cached_init_connectors(cfg)`` for initialization.

    Returns
    -------
    BackendContainer
        A BackendContainer from ``uscgaux.backends`` 
    """
    config = load_config_by_context()
    
    try:
        *_, backend_connectors = stu.cached_init_connectors(config)
        if backend_connectors is None:  # defensive: avoid caching a bad init
            logger.error("stu.cached_init_connectors returned None; stopping initialization")
            st.error("⚠️ Could not initialize backends. See logs for details.")
            st.stop()  # NoReturn
        return backend_connectors
    except Exception:
        logger.exception("BackendContainer unavailable (uscgaux required).")
        st.error("⚠️ Could not initialize backends. See logs for details.")
        st.stop()  # NoReturn



@st.cache_data(show_spinner=False, hash_funcs={BackendContainer: lambda obj: f"BackendContainer-{id(obj)}"})
def fetch_table_and_date(backend_connectors: BackendContainer) -> Tuple[pd.DataFrame, str]:
    """Return the catalog DataFrame and its last modified timestamp.

     This helper relies on the active ``CatalogConnector`` provided by the
    ``BackendContainer``. No direct Google Sheets or Drive fallback is used.

    Parameters
    ----------
    backend_connectors : BackendContainer
        The backend container instance that provides access to the catalog.

    Returns
    -------
    tuple[pd.DataFrame, str]
        - A DataFrame of the catalog filtered to rows with ``status="live"``.
        - An ISO 8601–formatted UTC string representing the last modified time.

    Raises
    ------
    RuntimeError
        If the catalog cannot be accessed, is empty, or cannot be converted
        for use in Streamlit.
    """
    logger.info("fetching catalog and date...")
    core_df = backend_connectors.catalog.fetch_table_and_normalize_catalog_df_for_core()
    if core_df is None or (isinstance(core_df, pd.DataFrame) and core_df.empty):
        logger.error("No catalog accessed or catalog is empty")
        raise RuntimeError("Catalog is unavailable or empty")
    
    st_df = stu.normalize_core_catalog_df_to_streamlit(core_df, ["live"])
    if st_df is None or (isinstance(st_df, pd.DataFrame) and st_df.empty):
        logger.error("Failed to convert catalog to Streamlit")
        raise RuntimeError("Failed to convert catalog to Streamlit")

    
    modified_time = backend_connectors.catalog.get_catalog_modified_time()
    
    logger.info("✅ Catalog successfully fetched")
    
    return st_df, modified_time
