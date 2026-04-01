"""Tests for the A2L calibration file parser."""

from pathlib import Path

import pytest

from agent.parsers.a2l_parser import A2LParser, A2LInfo, A2LObject

FIXTURES = Path(__file__).parent / "fixtures"
DFC_NAME = "DFC_rbe_CddUTnet_UTnet1Plaus"


class TestA2LParserParseFile:
    def test_returns_a2l_info_object(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert isinstance(result, A2LInfo)
        assert result.dfc_name == DFC_NAME

    def test_finds_measurements(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert len(result.measurements) > 0

    def test_measurement_names_contain_utnet1(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert all("UTnet1" in m.name or "utnet1" in m.name.lower() for m in result.measurements)

    def test_measurement_has_datatype(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        for measurement in result.measurements:
            assert "DATATYPE" in measurement.attributes

    def test_finds_characteristics(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert len(result.characteristics) > 0

    def test_characteristic_names_contain_utnet1(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert all(
            "UTnet1" in c.name or "utnet1" in c.name.lower()
            for c in result.characteristics
        )

    def test_file_reference_recorded(self):
        parser = A2LParser()
        result = parser.parse_file(FIXTURES / "CddUTnet.a2l", DFC_NAME)
        assert len(result.file_references) == 1
        assert result.file_references[0].endswith("CddUTnet.a2l")

    def test_unrelated_file_returns_empty(self, tmp_path):
        a2l = tmp_path / "other.a2l"
        a2l.write_text(
            '/begin MEASUREMENT SomeOtherSignal ""\n'
            "  DATATYPE UBYTE\n"
            "/end MEASUREMENT\n"
        )
        parser = A2LParser()
        result = parser.parse_file(a2l, DFC_NAME)
        assert result.measurements == []
        assert result.characteristics == []
        assert result.file_references == []


class TestA2LParserSearchDirectory:
    def test_finds_a2l_file(self):
        parser = A2LParser()
        result = parser.search_directory(FIXTURES, DFC_NAME)
        assert any("CddUTnet.a2l" in ref for ref in result.file_references)

    def test_no_duplicates_in_file_references(self):
        parser = A2LParser()
        result = parser.search_directory(FIXTURES, DFC_NAME)
        assert len(result.file_references) == len(set(result.file_references))

    def test_empty_directory_returns_empty(self, tmp_path):
        parser = A2LParser()
        result = parser.search_directory(tmp_path, DFC_NAME)
        assert result.measurements == []
        assert result.characteristics == []


class TestA2LTokenMatching:
    """Unit tests for the internal token-matching helpers."""

    def test_dfc_tokens_excludes_dfc_prefix(self):
        tokens = A2LParser._dfc_tokens("DFC_rbe_CddUTnet_UTnet1Plaus")
        assert "dfc" not in tokens
        assert "cddutnet" in tokens
        assert "utnet1plaus" in tokens

    def test_name_is_relevant_positive(self):
        tokens = A2LParser._dfc_tokens(DFC_NAME)
        assert A2LParser._name_is_relevant("Rbe_CddUTnet_UTnet1PlausStatus", tokens)

    def test_name_is_relevant_negative(self):
        tokens = A2LParser._dfc_tokens(DFC_NAME)
        assert not A2LParser._name_is_relevant("EngineSpeed", tokens)
