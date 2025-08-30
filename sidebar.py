# sidebar.py
import streamlit as st
from utils import ui_utils
from typing import List
try:
    # External stable API for allowed values
    from uscgaux import get_allowed_values
except Exception:  # pragma: no cover - fallback when dependency not available locally
    get_allowed_values = None  # type: ignore[assignment]

__all__ = ["build_sidebar"]          # so autoflake/ruff know what’s public

def build_sidebar():
    """Render the sidebar controls and return selected filter conditions.

    Returns
    -------
    dict
        Filter conditions with keys: `public_release`, `exclude_expired`,
        `scope` ("National" | "District" | "Both"), and optional `units` (list[str]).
    """

    # st.sidebar.markdown(
    #    "#### Experimental\n\n  The following features are experimental and may not work as # expected.\n\n"
    #)

    # Scope selection derived from shared schema when available
    default_scopes: List[str]
    if get_allowed_values is not None:
        try:
            # Base scopes from the shared schema
            default_scopes = [str(x) for x in get_allowed_values("scope")]
        except Exception:
            default_scopes = ["National", "District"]
    else:
        default_scopes = ["National", "District"]

    # Build options from schema and include a combined option "Both"
    # Fallback to known values if schema is unavailable/empty
    base_opts = default_scopes if default_scopes else ["National", "District"]
    scope_options = list(dict.fromkeys([*base_opts, "Both"]))
    # Radio defaults to National
    scope_choice = st.sidebar.radio(
        "Include documents at the following levels:", options=scope_options, index=0, horizontal=False
    )

    # District(s) multi-select (only relevant when District or Both)
    units_options: List[str] = []
    if get_allowed_values is not None:
        try:
            units_options = [str(x) for x in get_allowed_values("unit", {"scope": "District"})]
        except Exception:
            units_options = []

    selected_units: List[str] = []
    if scope_choice in ("District", "Both"):
        selected_units = st.sidebar.multiselect(
            "Select your District(s)", options=units_options, default=[],
            help="Choose one or more districts to include"
        )

    st.sidebar.divider()
    # Expiration filter
    exclude_expired = st.sidebar.checkbox("Exclude expired documents", value=True)
    st.sidebar.caption(
        "This excludes all Commandant Instructions issued more than 12 years ago (including AUXMAN) as well as ALCOASTs and ALAUXs issued more than one year ago, per COMDTINST 5215.6J.\n\n"
    )

    filter_conditions: dict = {"public_release": True, "scope": scope_choice}
    if exclude_expired:
        filter_conditions["exclude_expired"] = True
    if selected_units:
        filter_conditions["units"] = selected_units

    return filter_conditions
