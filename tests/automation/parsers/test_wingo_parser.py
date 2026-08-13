"""Tests para Wingo Parser."""

import pytest

from apps.automation.parsers.console_parser import ConsoleParser


@pytest.fixture
def console_parser():
    return ConsoleParser()


class TestWingoConsole:
    def test_parse_wingo_text(self, console_parser):
        text = "WINGO VUELO CONFIRMACION\nCODIGO: WG1234"
        result = console_parser.parse(text)
        assert isinstance(result, dict)
