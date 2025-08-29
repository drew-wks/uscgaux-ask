import pytest


def test_uscgaux_present():
    """Verify the external schema package `uscgaux` is importable.

    Skips the test with a clear reason if not installed, so the
    rest of the suite can continue.
    """
    mod = pytest.importorskip("uscgaux", reason="uscgaux package not installed. Install via requirements.txt")
    # Basic API presence check
    assert hasattr(mod, "get_allowed_values"), "uscgaux.get_allowed_values missing"


def test_uscgaux_api_allowed_values():
    """Ensure `get_allowed_values` exists and returns lists for known fields."""
    ux = pytest.importorskip("uscgaux")
    get_allowed_values = getattr(ux, "get_allowed_values", None)
    assert callable(get_allowed_values), "get_allowed_values is not callable"

    # Scopes should be a list; content may vary by schema version
    scopes = get_allowed_values("scope")
    assert isinstance(scopes, list), "get_allowed_values('scope') did not return a list"
    assert all(isinstance(s, str) for s in scopes), "Scope values should be strings"

    # Units for district context should be a list (may be empty depending on schema contents)
    units = get_allowed_values("unit", {"scope": "District"})
    assert isinstance(units, list), "get_allowed_values('unit', {'scope': 'District'}) did not return a list"


def test_uscgaux_api_functions_callable():
    """Check presence and callability of the stable schema API functions."""
    from pytest import importorskip

    ux = importorskip("uscgaux")

    # Required functions
    for name in (
        "get_catalog_schema",
        "get_allowed_values",
        "get_editable_fields",
        "get_read_only_fields",
        "get_user_required_fields",
        "get_system_required_fields",
    ):
        fn = getattr(ux, name, None)
        assert callable(fn), f"uscgaux.{name} is missing or not callable"

    # Light touch invocation to ensure they run without raising
    ux.get_allowed_values("scope")
    ux.get_allowed_values("unit", {"scope": "District"})

    # The following should return collections/structures; we only ensure no exceptions
    ux.get_catalog_schema()
    ux.get_editable_fields()
    ux.get_read_only_fields()
    ux.get_user_required_fields()
    ux.get_system_required_fields()

