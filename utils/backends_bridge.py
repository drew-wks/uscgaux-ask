from __future__ import annotations

import logging
import pandas as pd
import streamlit as st


from uscgaux import stu
from uscgaux.config.loader import load_config_by_context
from uscgaux.backends import BackendContainer
from .protocols import CatalogConnectorProtocol, VectorDBConnectorProtocol
from typing import Any, Iterable


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)



@st.cache_resource(show_spinner=True)
def get_backend_container() -> BackendContainer:
    """Return a cached BackendContainer

    Loads the active configuration via ``load_config_by_context()`` and passes
    it into ``stu.cached_init_connectors(config)`` for initialization.

    Returns
    -------
    BackendContainer
        A BackendContainer from ``uscgaux.backends`` 
    """
    config = load_config_by_context()
    
    try:
        backend_connectors = stu.cached_init_connectors(config)[-1]
        if backend_connectors is None:  # defensive: avoid caching a bad init
            logger.error("stu.cached_init_connectors returned None; stopping initialization")
            st.error("⚠️ Could not initialize backends. See logs for details.")
            st.stop()  # NoReturn
        return backend_connectors
    except Exception:
        logger.exception("BackendContainer unavailable (uscgaux required).")
        st.error("⚠️ Could not initialize backends. See logs for details.")
        st.stop()  # NoReturn: ensure no None return paths




@st.cache_resource(show_spinner=False)
def get_runtime_config() -> dict:
    """Return the active configuration mapping loaded by ``uscgaux``.

    This isolates configuration loading/caching to avoid passing unhashable
    structures through Streamlit cache boundaries. Other modules should call
    this accessor instead of importing the loader directly.

    Returns
    -------
    dict
        The configuration mapping from ``uscgaux.config.loader``.
    """
    try:
        return load_config_by_context()
    except Exception:
        logger.exception("Failed to load runtime config via uscgaux loader")
        st.error("⚠️ Could not load configuration. See logs for details.")
        st.stop()  # NoReturn


def config(path: Iterable[str] | str) -> Any:
    """Access a nested configuration value without fallbacks.

    Accepts either a list/tuple of keys or a dot-delimited string and returns
    the nested value. If any key is missing, raises ``KeyError`` with a helpful
    message. This intentionally avoids defaults/fallbacks to surface misconfigurations
    early.

    Parameters
    ----------
    path : Iterable[str] | str
        The key path to traverse, e.g., ["RAG", "RETRIEVAL", "k"] or
        "RAG.RETRIEVAL.k".

    Returns
    -------
    Any
        The value stored at the provided path.

    Raises
    ------
    KeyError
        If any segment of the path is missing in the configuration mapping.
    TypeError
        If ``path`` is not an iterable of strings or a string.
    """
    cfg = get_runtime_config()

    if isinstance(path, str):
        keys = [k for k in path.split(".") if k]
    elif isinstance(path, Iterable):
        keys = list(path)
    else:
        raise TypeError("path must be a list/tuple of strings or a dot string")

    cur: Any = cfg
    traversed: list[str] = []
    for key in keys:
        traversed.append(str(key))
        if not isinstance(cur, dict) or key not in cur:
            joined = "/".join(traversed)
            raise KeyError(f"Missing configuration at '{joined}' (key '{key}' not found)")
        cur = cur[key]
    return cur

@st.cache_data(show_spinner=False)
def fetch_table_and_date_from_catalog() -> tuple[pd.DataFrame, str]:
    """Return the catalog DataFrame and its last modified timestamp using a connector.

    Parameters
    ----------
    None

    Returns
    -------
    tuple[pd.DataFrame, str]
        Filtered DataFrame (status="live") and ISO 8601 or epoch modified time string.

    Raises
    ------
    RuntimeError
        If the catalog cannot be accessed, is empty, or cannot be converted.
    """
    logger.info("fetching catalog and date via connector...")
    catalog: CatalogConnectorProtocol = get_catalog_connector()
    core_df = catalog.fetch_table_and_normalize_catalog_df_for_core()
    if core_df is None or (isinstance(core_df, pd.DataFrame) and core_df.empty):
        logger.error("No catalog accessed or catalog is empty")
        raise RuntimeError("Catalog is unavailable or empty")

    st_df = stu.normalize_core_catalog_df_to_streamlit(core_df, ["live"])
    if st_df is None or (isinstance(st_df, pd.DataFrame) and st_df.empty):
        logger.error("Failed to convert catalog to Streamlit")
        raise RuntimeError("Failed to convert catalog to Streamlit")

    modified_time = catalog.get_catalog_modified_time()

    logger.info("✅ Catalog successfully fetched via connector")
    return st_df, str(modified_time) if modified_time is not None else "--"


@st.cache_resource(show_spinner=False)
def get_catalog_connector() -> CatalogConnectorProtocol:
    """Return the active catalog connector using the container boundary."""
    container = get_backend_container()
    return container.catalog  # type: ignore[return-value]


@st.cache_resource(show_spinner=False)
def get_vectordb_connector() -> VectorDBConnectorProtocol:
    """Return the active vector DB connector using the container boundary."""
    container = get_backend_container()
    return container.vectordb  # type: ignore[return-value]
