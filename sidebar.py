# sidebar.py
from typing import List
import streamlit as st
from uscgaux import get_allowed_values  # hard dependency
from utils.filter_spec import get_local_filter_field_names


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

    # Determine which filters this app actually supports (Phase 1: local spec)
    active_fields = get_local_filter_field_names()

    # Scope selection derived from shared schema when available
    default_scopes: List[str]
    # Base scopes from the shared schema
    try:
        default_scopes = [str(x) for x in get_allowed_values("scope")]
    except Exception:
        # If schema cannot be read at runtime, degrade to known values
        default_scopes = ["National", "District"]

    scope_choice = None
    if "scope" in active_fields:
        # Build options from schema and include a combined option "Both"
        # Fallback to known values if schema is unavailable/empty
        base_opts = default_scopes if default_scopes else ["National", "District"]
        scope_options = list(dict.fromkeys([*base_opts, "Both"]))
        # Radio defaults to National
        scope_choice = st.sidebar.radio(
            "Include documents at the following levels:", options=scope_options, index=0, horizontal=False
        )

    # District(s) multi-select (only relevant when District or Both)
    selected_units: List[str] = []
    if "unit" in active_fields and scope_choice in ("District", "Both"):
        units_options: List[str] = []
        try:
            units_options = [str(x) for x in get_allowed_values("unit", {"scope": "District"})]
        except Exception:
            units_options = []
        selected_units = st.sidebar.multiselect(
            "Select your District(s)", options=units_options, default=[],
            help="Choose one or more districts to include"
        )

    # Visual separator (older Streamlit or test spies may not implement divider)
    try:
        st.sidebar.divider()
    except Exception:
        st.sidebar.markdown("---")
    # Expiration filter
    exclude_expired = False
    if "exclude_expired" in active_fields:
        exclude_expired = st.sidebar.checkbox("Exclude expired documents", value=True)
        st.sidebar.caption(
            "This excludes all Commandant Instructions issued more than 12 years ago (including AUXMAN) as well as ALCOASTs and ALAUXs issued more than one year ago, per COMDTINST 5215.6J.\n\n"
        )

    filter_conditions: dict = {}
    if "public_release" in active_fields:
        filter_conditions["public_release"] = True
    if scope_choice is not None:
        filter_conditions["scope"] = scope_choice
    if exclude_expired:
        filter_conditions["exclude_expired"] = True
    if selected_units:
        filter_conditions["units"] = selected_units

    return filter_conditions
