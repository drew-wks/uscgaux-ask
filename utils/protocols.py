"""Typed interfaces for provider adapters and schema.

These Protocols decouple our code from concrete implementations in the
external `uscgaux` package and make testing/mocking straightforward.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class CatalogConnectorProtocol(Protocol):
    """Provider adapter interface for catalog access."""

    def get_catalog(self) -> pd.DataFrame:  # pragma: no cover - signature only
        ...

    def get_catalog_modified_time(self) -> str | datetime:  # pragma: no cover
        ...


@runtime_checkable
class BackendContainerProtocol(Protocol):
    """Top-level container of connectors provided by `uscgaux.backends`."""

    catalog: CatalogConnectorProtocol
    catalog_archive: CatalogConnectorProtocol


@runtime_checkable
class SchemaAPIProtocol(Protocol):
    """Schema API surface offered by the `uscgaux` package."""

    def get_allowed_values(self, field: str, context: dict | None = None) -> list[str]:  # pragma: no cover
        ...

    def get_catalog_schema(self) -> dict:  # pragma: no cover
        ...
