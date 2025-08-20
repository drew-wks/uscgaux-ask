import os
import pandas as pd
from datetime import datetime
import json
import gspread
import streamlit as st
from googleapiclient.discovery import build, Resource as DriveClient
from gspread.client import Client as SheetsClient
from google.oauth2.service_account import Credentials



def get_gcp_credentials() -> Credentials:
    """
    Returns a Google `Credentials` object from a flattened JSON string in the environment.
    """
    creds_json = st.secrets["GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP"]
    if not creds_json:
        raise EnvironmentError("Missing GCP_CREDENTIALS_FOR_STREAMLIT_USCGAUX_APP in environment.")
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict)
        return creds
    except Exception as e:
        raise ValueError(f"Failed to load GCP credentials from environment: {e}") from e
    
    
def init_drive_client(creds: Credentials) -> DriveClient:
    """
    Initializes a Google Drive client using the provided credentials.

    Applies the required Drive API scopes to the provided credentials and returns
    an authorized `googleapiclient.discovery.Resource` object for interacting with
    the Drive v3 API.

    Args:
        creds (Credentials): Google service account or user credentials.

    Returns:
        DriveClient: An authorized client for the Google Drive API.
    """
    scoped_creds = creds.with_scopes(["https://www.googleapis.com/auth/drive"])
    client = build("drive", "v3", credentials=scoped_creds)
    os.write(1, "✅ Google Drive client initialized successfully with scoped credentials.".encode())
    return client

    
def init_sheets_client(creds: Credentials) -> SheetsClient:
    """
    Initializes a Google Sheets client using the provided credentials.

    Applies the necessary scopes for accessing both Sheets and Drive APIs,
    and returns a `gspread` client authorized with those credentials.

    Args:
        creds (Credentials): Google service account or user credentials.

    Returns:
        SheetsClient: An authorized `gspread` client for accessing Google Sheets.
    """
    scoped_creds = creds.with_scopes([
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ])
    client = gspread.authorize(scoped_creds)
    os.write(1, "✅ Google Sheets client initialized successfully with scoped credentials.".encode())
    return client


@st.cache_data
def load_registry_and_date() -> tuple[pd.DataFrame, str]:
    """
    Gets the LIBRARY_UNIFIED registry (status=live only) as a DataFrame and the last modified timestamp.
    
    Returns:
        Tuple containing:
            - DataFrame: the sheet data
            - str: ISO-formatted last modified time (UTC)
    """
    creds = get_gcp_credentials()
    spreadsheet_id = st.secrets["CATALOG_ID"]
    
    drive_client = init_drive_client(creds)
    sheets_client = init_sheets_client(creds)
    
    try:
        sheet = sheets_client.open_by_key(spreadsheet_id).sheet1
        if sheet is None:
            os.write(2, "❌ Worksheet could not be fetched".encode())
            return pd.DataFrame(), ""

        raw_data = sheet.get_all_values()
        if not raw_data or len(raw_data) < 2:
            os.write(2, "❌ Worksheet has no data rows".encode())
            return pd.DataFrame(columns=raw_data[0] if raw_data else []), ""

        headers = raw_data[0]
        rows = raw_data[1:]

        df = pd.DataFrame(rows, columns=headers)
        df = df.loc[:, [col.strip() != "" for col in df.columns]]
        df = df.fillna("").astype(str)
        df = df[df["status"].str.strip().str.lower() == "live"]

        os.write(1, "✅ Fetched and converted worksheet".encode())
        
        file_metadata = drive_client.files().get(
            fileId=spreadsheet_id,
            fields="modifiedTime"
        ).execute() # type: ignore[attr-defined]
        formatted_modified_time = datetime.strptime(file_metadata["modifiedTime"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m-%dT%H:%M:%SZ")
        return df, formatted_modified_time

    except Exception as e:
        os.write(2, f"❌ [load_registry] Error: {e}".encode())
        return pd.DataFrame(), ""
