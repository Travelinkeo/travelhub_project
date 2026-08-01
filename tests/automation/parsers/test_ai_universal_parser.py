"""Tests para AI Universal Parser."""

import pytest

from apps.automation.parsers.ai_universal_parser import UniversalAIParser


@pytest.mark.unit
@pytest.fixture
def ai_parser():
    return UniversalAIParser()


@pytest.mark.unit
class TestAIUniversalParserDetection:
    def test_can_parse_universal(self, ai_parser):
        # Universal parser should be fallback
        text = "ANY TEXT"
        assert ai_parser.can_parse(text) is True


@pytest.mark.unit
class TestAIUniversalParserEdgeCases:
    def test_empty_text(self, ai_parser):
        result = ai_parser.parse("")
        assert "error" in result
