"""Tests para TK Connect / Console Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestTKConnectConsole:
    def test_parse_tk_text(self, console_parser):
        text = "TURKISH AIRLINES CONNECT RECEIPT\nPNR: TK1234"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
