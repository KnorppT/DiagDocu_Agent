"""Tests for the core DiagDocu generation logic."""

from pathlib import Path

import pytest

from agent.diagdocu import extract_dfc_name, generate_diagdocu

FIXTURES = Path(__file__).parent / "fixtures"
DFC_NAME = "DFC_rbe_CddUTnet_UTnet1Plaus"


class TestExtractDfcName:
    def test_extracts_from_german_request(self):
        msg = "Erstelle die DiagDocu für DFC_rbe_CddUTnet_UTnet1Plaus"
        assert extract_dfc_name(msg) == "DFC_rbe_CddUTnet_UTnet1Plaus"

    def test_extracts_from_english_request(self):
        msg = "Please generate documentation for DFC_rbe_CddUTnet_UTnet1Plaus."
        assert extract_dfc_name(msg) == "DFC_rbe_CddUTnet_UTnet1Plaus"

    def test_extracts_from_bare_name(self):
        assert extract_dfc_name("DFC_rbe_CddUTnet_UTnet1Plaus") == "DFC_rbe_CddUTnet_UTnet1Plaus"

    def test_returns_first_match_when_multiple(self):
        msg = "Compare DFC_Foo and DFC_Bar"
        assert extract_dfc_name(msg) == "DFC_Foo"

    def test_returns_none_when_no_dfc(self):
        assert extract_dfc_name("Hello world") is None

    def test_returns_none_for_empty_string(self):
        assert extract_dfc_name("") is None


class TestGenerateDiagdocuTemplate:
    """Tests for generate_diagdocu without source files (template mode)."""

    def test_returns_string(self):
        result = generate_diagdocu(DFC_NAME)
        assert isinstance(result, str)

    def test_contains_dfc_name(self):
        result = generate_diagdocu(DFC_NAME)
        assert DFC_NAME in result

    def test_contains_all_sections(self):
        result = generate_diagdocu(DFC_NAME)
        for section in [
            "Übersicht",
            "Eingangsgrößen",
            "Fehlerbedingungen",
            "Fehlerspeicherung",
            "Kalibrierparameter",
            "Quellcode-Referenzen",
        ]:
            assert section in result, f"Section '{section}' missing from output"

    def test_is_valid_markdown_heading(self):
        result = generate_diagdocu(DFC_NAME)
        assert result.startswith("# DiagDocu:")

    def test_nonexistent_source_root_falls_back_to_template(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        result = generate_diagdocu(DFC_NAME, source_root=nonexistent)
        assert DFC_NAME in result
        assert "Übersicht" in result


class TestGenerateDiagdocuWithSources:
    """Tests for generate_diagdocu with real fixture source files."""

    def test_includes_source_file_reference(self):
        result = generate_diagdocu(DFC_NAME, source_root=FIXTURES)
        # The document should mention the C or H file
        assert ".c" in result or ".h" in result

    def test_includes_a2l_measurements(self):
        result = generate_diagdocu(DFC_NAME, source_root=FIXTURES)
        assert "UTnet1" in result

    def test_includes_macros_from_c_file(self):
        result = generate_diagdocu(DFC_NAME, source_root=FIXTURES)
        # Macros defined with the DFC name should appear
        assert "THRESHOLD" in result or "DEBOUNCE" in result or DFC_NAME in result

    def test_no_empty_document(self):
        result = generate_diagdocu(DFC_NAME, source_root=FIXTURES)
        assert len(result) > 200
