from typing import List, Optional
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

    must: list[models.FieldCondition] = []
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
    filter_conditions: Optional[dict[str, str | bool | None]] = None,
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

    scope_val = fc.get("scope")
    unit_val = fc.get("unit")

    if scope_val and scope_val.lower() != "national":
        district = df[df["scope"].str.lower() == scope_val.lower()]
        if unit_val:
            district = district[district["unit"].str.lower() == str(unit_val).lower()]
        national = df[df["scope"].str.lower() == "national"]
        df = pd.concat([district, national], ignore_index=True)
    elif scope_val and scope_val.lower() == "national":
        df = df[df["scope"].str.lower() == "national"]
        if unit_val:
            df = df[df["unit"].str.lower() == str(unit_val).lower()]
    elif unit_val:
        df = df[df["unit"].str.lower() == str(unit_val).lower()]

    if "pdf_id" not in df.columns:
        return []

    return df["pdf_id"].dropna().astype(str).unique().tolist()
