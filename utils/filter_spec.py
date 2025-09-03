"""Local filter specification and validation utilities.

This module defines the set of filters that uscgaux-ask actually uses
and a validator that checks these choices against the upstream schema.

Phase 1 goal: keep behavior under local control, use upstream only as
an upper-bound validator. No dynamic UI or auto-added filters.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional, Set
import logging


logger = logging.getLogger(__name__)


# App-level types for filters used by this project
FilterKind = Literal["enum", "date", "text", "flag"]


@dataclass(frozen=True)
class FilterField:
    """Local filter field declaration.

    Attributes
    ----------
    name: str
        Field name (matches catalog column when applicable).
    kind: FilterKind
        App-level type: "enum" | "date" | "text" | "flag".
    label: Optional[str]
        Optional UI label. Not used for dynamic generation in Phase 1.
    operators: Optional[List[str]]
        Optional operator list for future use. Informational only in Phase 1.
    order: Optional[int]
        Optional order hint for UI. Informational only in Phase 1.
    """

    name: str
    kind: FilterKind
    label: Optional[str] = None
    operators: Optional[List[str]] = None
    order: Optional[int] = None


def get_local_filter_spec() -> List[FilterField]:
    """Return the project's local filter spec.

    The list below is the single source of truth for which fields this
    project supports as filters in Phase 1. Upstream schema does not
    auto-add to this set; it is only used for validation.
    """
    return [
        # Scope selection (National | District | Both via UI logic)
        FilterField(name="scope", kind="enum", label="Scope", order=10, operators=["equals"]),
        # District(s)
        FilterField(name="unit", kind="enum", label="District", order=20, operators=["equals", "in"]),
        # Expiration toggle is derived locally from expiration_date
        FilterField(name="exclude_expired", kind="flag", label="Exclude expired", order=30),
        # Always filter to public_release documents
        FilterField(name="public_release", kind="flag", label="Public release only", order=5),
    ]


def get_local_filter_field_names() -> Set[str]:
    """Return the set of filter field names used by this app."""
    return {f.name for f in get_local_filter_spec()}


def validate_local_spec_against_upstream(strict: bool = False) -> bool:
    """Validate local filter fields against upstream capabilities.

    The upstream schema's `is_filterable` (via `get_filterable_fields`) is used
    as an upper bound. Local fields not present upstream are flagged. Derived
    local flags (e.g., `exclude_expired`) are allowed and skipped.

    Additionally, if the Streamlit column config builder is available, check
    for a coarse kind compatibility (enum vs date) and log warnings if the
    inferred UI control differs from expectations.

    Parameters
    ----------
    strict : bool, default False
        If True, raise an exception on validation failure; otherwise log
        warnings and continue.

    Returns
    -------
    bool
        True if validation passes (or is skipped), False if issues found
        and `strict` is False.
    """
    local_fields = get_local_filter_spec()
    local_names = {f.name for f in local_fields}

    # Fields that are local-only derived controls, not present as-is upstream
    derived_ok: Set[str] = {"exclude_expired"}

    issues: List[str] = []

    # 1) Validate with upstream get_filterable_fields if available
    filterable_upstream: Optional[Set[str]] = None
    try:
        # Defer import to runtime; package may not be present during tests
        from uscgaux.utils.catalog_schema_utils import get_filterable_fields  # type: ignore

        try:
            upstream_fields = get_filterable_fields()
            if isinstance(upstream_fields, (list, tuple)):
                filterable_upstream = {str(x) for x in upstream_fields}
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Upstream get_filterable_fields() error: %s", exc)
    except Exception:
        # If not available, skip this check
        logger.info("Upstream schema_util.get_filterable_fields not available; skipping filterability check")

    if filterable_upstream is not None:
        for f in local_fields:
            if f.name in derived_ok:
                continue
            if f.name not in filterable_upstream:
                issues.append(f"Local filter '{f.name}' is not marked filterable upstream")

    # 2) Coarse-kind compatibility using Streamlit column config builder
    try:
        from uscgaux.frontends.streamlit.column_config import (  # type: ignore
            build_streamlit_column_config,
        )

        try:
            column_config: dict = build_streamlit_column_config(None)
        except Exception:  # builder may accept no args; fallback
            column_config = build_streamlit_column_config()

        # Best-effort inference: map builder column types to app-level kinds
        def infer_kind(obj: object) -> Optional[FilterKind]:
            tname = type(obj).__name__
            if "Selectbox" in tname:
                return "enum"
            if "Datetime" in tname:
                return "date"
            if "Text" in tname:
                return "text"
            return None

        for f in local_fields:
            if f.name in derived_ok:
                continue
            cfg = column_config.get(f.name)
            if cfg is None:
                # If upstream has no column config, skip
                continue
            inferred = infer_kind(cfg)
            if inferred and inferred != f.kind:
                issues.append(
                    f"Kind mismatch for '{f.name}': local={f.kind} upstream-ui={inferred}"
                )
    except Exception:
        # Builder not available; skip UI-kind check
        logger.info("Streamlit column config builder not available; skipping UI-kind check")

    if issues:
        msg = "; ".join(issues)
        if strict:
            raise RuntimeError(f"FilterSpec validation failed: {msg}")
        logger.warning("FilterSpec validation issues: %s", msg)
        return False

    logger.info("FilterSpec validation passed for fields: %s", ", ".join(sorted(local_names)))
    return True


