"""Tests para Travelport / Console Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestTravelportConsole:
    def test_parse_travelport_text(self, console_parser):
        text = "TRAVELPORT GALILEO ITINERARY\nPNR: 1A2B3C"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
