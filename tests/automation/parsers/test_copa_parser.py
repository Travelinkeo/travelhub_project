"""Tests para Copa / Console Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestCopaParserConsole:
    def test_parse_copa_text(self, console_parser):
        text = "COPA AIRLINES\nCOPAAIRLINES.COM\nCOMPROBANTE DE PAGO\nRESERVA ABC123"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
