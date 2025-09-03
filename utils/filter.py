from typing import List, Optional, Iterable
from datetime import datetime, timezone
import pandas as pd
from qdrant_client.http import models



def build_retrieval_filter(
    filter_conditions: Optional[dict[str, str | bool | None]] = None,
    allowed_pdf_ids: Optional[List[str]] = None,
) -> Optional[models.Filter]:
    """Return a Qdrant filter limited to ``pdf_id`` values.

    All other filtering is handled using the catalog.
    """

    must: list[models.Condition] = []  
    if allowed_pdf_ids is not None:
        must.append(
            models.FieldCondition(
                key="metadata.pdf_id",
                match=models.MatchAny(any=allowed_pdf_ids),
            )
        )

    return models.Filter(must=must) if must else None


def catalog_filter(
    catalog_df: pd.DataFrame,
    filter_conditions: Optional[dict[str, str | bool | None | List[str]]] = None,
) -> List[str]:
    """Return a list of ``pdf_id`` values from ``catalog_df`` that satisfy
    ``filter_conditions``.

    Parameters
    ----------
    catalog_df : pandas.DataFrame
        catalog data with at least ``pdf_id``, ``scope`` and ``expiration_date``
        columns.
    filter_conditions : dict, optional
        Same structure as ``build_retrieval_filter`` accepts.

    Returns
    -------
    list[str]
        Unique ``pdf_id`` values matching the filter conditions.
    """
    fc = (filter_conditions or {}).copy()
    df = catalog_df.copy()

    # Apply boolean flag filters
    for flag in ("public_release", "aux_specific"):
        if flag in df.columns and flag in fc:
            val = fc.pop(flag)
            df = df[df[flag].astype(str).str.lower() == str(val).lower()]

    if fc.pop("exclude_expired", False) and "expiration_date" in df.columns:
        now = datetime.now(timezone.utc)
        exp = pd.to_datetime(df["expiration_date"], errors="coerce", utc=True)
        df = df[(exp.isna()) | (exp > now)]

    scope_val_raw = fc.get("scope")
    scope_val = str(scope_val_raw).strip().lower() if scope_val_raw else None

    # Support multi-district selection via `units` and single via `unit`
    units_sel = fc.get("units")  # may be list[str]
    unit_val = fc.get("unit")
    units: List[str] = []
    if isinstance(units_sel, Iterable) and not isinstance(units_sel, (str, bytes)):
        units = [str(u).strip().lower() for u in units_sel]
    elif unit_val:
        units = [str(unit_val).strip().lower()]

    # Normalize column values safely
    if "scope" in df.columns:
        df["scope"] = df["scope"].astype(str)
    if "unit" in df.columns:
        df["unit"] = df["unit"].astype(str)

    # Apply scope/unit logic
    if scope_val == "national":
        df = df[df["scope"].str.lower() == "national"]
        # units typically don't apply to national docs; ignore units
    elif scope_val == "district":
        df = df[df["scope"].str.lower() == "district"]
        if units:
            df = df[df["unit"].str.lower().isin(units)]
    elif scope_val == "both":
        nat = df[df["scope"].str.lower() == "national"]
        dist = df[df["scope"].str.lower() == "district"]
        if units:
            dist = dist[dist["unit"].str.lower().isin(units)]
        df = pd.concat([nat, dist], ignore_index=True)
    else:
        # No explicit scope; if units provided, filter district by units, otherwise leave as-is
        if units:
            dist = df[(df["scope"].str.lower() == "district") & (df["unit"].str.lower().isin(units))]
            nat = df[df["scope"].str.lower() == "national"]
            df = pd.concat([nat, dist], ignore_index=True)

    if "pdf_id" not in df.columns:
        return []

    return df["pdf_id"].dropna().astype(str).unique().tolist()
