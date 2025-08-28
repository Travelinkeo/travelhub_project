import pytest
from django.test import override_settings
from core.utils import sanitize_passenger_name

@pytest.mark.unit
@override_settings(PASSENGER_FIRST_NAME_WHITELIST=["PANAMA"])  # For test, treat PANAMA as a valid first name
def test_whitelist_override_preserves_token():
    raw = "PEREZ/PANAMA"
    assert sanitize_passenger_name(raw) == "PEREZ/PANAMA"

@pytest.mark.unit
@override_settings(PASSENGER_FIRST_NAME_WHITELIST="PANAMA,JOSE")
def test_whitelist_override_string_format():
    raw = "GONZALEZ/PANAMA"
    assert sanitize_passenger_name(raw) == "GONZALEZ/PANAMA"

@pytest.mark.unit
@override_settings(PASSENGER_FIRST_NAME_WHITELIST=["JOSE"])  # JOSE already default; ensure no regression
def test_default_name_still_preserved():
    raw = "RAMIREZ/JOSE"
    assert sanitize_passenger_name(raw) == "RAMIREZ/JOSE"
