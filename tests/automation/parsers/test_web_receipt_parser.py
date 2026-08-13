"""Tests para Web Receipt Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestWebReceiptConsole:
    def test_parse_web_receipt(self, console_parser):
        text = "WEB RECEIPT RECEIBO VUELO\nLOCALIZADOR: W1E2B3"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
