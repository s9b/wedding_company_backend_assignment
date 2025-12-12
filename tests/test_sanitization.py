import pytest

from ..app.routers.orgs import sanitize_org_name
from ..scripts.migrate_org_name import sanitize_name as script_sanitize_name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Acme Corp", "acme_corp"),
        ("Acme   Corp!", "acme_corp"),
        ("ACME-123", "acme123"),
        ("My.Org", "myorg"),
        ("  spaced  Name  ", "spaced_name"),
        ("UNDER_score", "under_score"),
    ],
)
def test_sanitize_org_name(raw: str, expected: str):
    assert sanitize_org_name(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Acme Corp",
        "ACME-123",
        "My.Org",
        "  spaced  Name  ",
        "UNDER_score",
    ],
)
def test_sanitize_functions_match(raw: str):
    # Ensure router and script sanitizers behave identically
    assert sanitize_org_name(raw) == script_sanitize_name(raw)


def test_sanitize_idempotent():
    val = "Acme   Corp!"
    once = sanitize_org_name(val)
    twice = sanitize_org_name(once)
    assert once == twice
