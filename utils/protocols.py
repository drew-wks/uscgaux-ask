"""Typed interfaces for connectors used by ASK.

These Protocols allow us to depend on a minimal surface area and avoid a hard
compile-time dependency on concrete classes from the `uscgaux` package in the
ask app code paths.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable, Any

import pandas as pd


@runtime_checkable
class CatalogConnectorProtocol(Protocol):
    """Provider adapter interface for catalog access used by ASK."""

    def fetch_table_and_normalize_catalog_df_for_core(self) -> pd.DataFrame:  # pragma: no cover - signature only
        ...

    def get_catalog_modified_time(self) -> str | datetime | float | None:  # pragma: no cover - implementation may vary
        ...


@runtime_checkable
class VectorDBConnectorProtocol(Protocol):
    """Minimal interface for the vector DB connector used by ASK."""

    def get_langchain_vectorstore(self) -> Any:  # pragma: no cover - returns a LangChain VectorStore
        ...

