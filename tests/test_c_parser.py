"""Tests for the C/H source file parser."""

from pathlib import Path

import pytest

from agent.parsers.c_parser import CFileParser, DFCInfo

FIXTURES = Path(__file__).parent / "fixtures"
DFC_NAME = "DFC_rbe_CddUTnet_UTnet1Plaus"


class TestCFileParserParseFile:
    def test_returns_dfc_info_object(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert isinstance(result, DFCInfo)
        assert result.name == DFC_NAME

    def test_finds_file_reference(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert any(DFC_NAME in ref for ref in result.file_references)

    def test_extracts_macros(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert any(DFC_NAME in m for m in result.macros)

    def test_extracts_function_signature(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert any(DFC_NAME in sig for sig in result.function_signatures)

    def test_extracts_enum_values(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert any(DFC_NAME in ev for ev in result.enum_values)

    def test_extracts_includes(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert "Dem.h" in result.includes

    def test_skips_unrelated_file(self, tmp_path):
        unrelated = tmp_path / "unrelated.c"
        unrelated.write_text("/* Nothing here */\nvoid foo(void) {}\n")
        parser = CFileParser()
        result = parser.parse_file(unrelated, DFC_NAME)
        assert result.file_references == []
        assert result.macros == []

    def test_extracts_block_comment(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.c", DFC_NAME)
        assert any(DFC_NAME in c for c in result.comments)

    def test_header_file(self):
        parser = CFileParser()
        result = parser.parse_file(FIXTURES / "DFC_rbe_CddUTnet_UTnet1Plaus.h", DFC_NAME)
        assert result.file_references != []
        assert any(DFC_NAME in m for m in result.macros)


class TestCFileParserSearchDirectory:
    def test_finds_both_c_and_h(self):
        parser = CFileParser()
        result = parser.search_directory(FIXTURES, DFC_NAME)
        extensions_found = {Path(r).suffix.lower() for r in result.file_references}
        assert ".c" in extensions_found
        assert ".h" in extensions_found

    def test_merges_macros_from_multiple_files(self):
        parser = CFileParser()
        result = parser.search_directory(FIXTURES, DFC_NAME)
        # The .h file defines DFC_rbe_CddUTnet_UTnet1Plaus_ID
        assert any("_ID" in m for m in result.macros)
        # The .c file defines _THRESHOLD and _DEBOUNCE
        assert any("_THRESHOLD" in m for m in result.macros)

    def test_no_duplicates_in_file_references(self):
        parser = CFileParser()
        result = parser.search_directory(FIXTURES, DFC_NAME)
        assert len(result.file_references) == len(set(result.file_references))

    def test_empty_directory_returns_empty_info(self, tmp_path):
        parser = CFileParser()
        result = parser.search_directory(tmp_path, DFC_NAME)
        assert result.file_references == []
        assert result.macros == []
