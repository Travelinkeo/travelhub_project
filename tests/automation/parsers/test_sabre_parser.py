"""Tests para Sabre / Console Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestSabreParserConsole:
    def test_parse_sabre_raw(self, console_parser):
        text = "1 AV4816K 03DEC BOGMAD HK1 0700 2330"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
        assert result.get("source_system") in ["SABRE", "UNKNOWN"]
