"""Core DiagDocu logic.

Orchestrates the C/H parser and A2L parser, then assembles a structured
Markdown documentation document for a given DFC.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .parsers.c_parser import CFileParser, DFCInfo
from .parsers.a2l_parser import A2LParser, A2LInfo


_DFC_RE = re.compile(r"\bDFC_\w+")

_REPO_URL = os.environ.get(
    "DIAGDOCU_REPO_URL",
    "https://github.com/KnorppT/DiagDocu_Agent",
)


def extract_dfc_name(message: str) -> str | None:
    """Return the first DFC identifier found in *message*, or ``None``."""
    m = _DFC_RE.search(message)
    return m.group(0) if m else None


def generate_diagdocu(
    dfc_name: str,
    source_root: Path | None = None,
) -> str:
    """Generate a Markdown DiagDocu for *dfc_name*.

    If *source_root* is provided the function attempts to extract information
    from C/H and A2L files found under that directory.  When no source root is
    given (or the directory contains no relevant files) a template document is
    returned instead.

    Parameters
    ----------
    dfc_name:
        The DFC identifier, e.g. ``DFC_rbe_CddUTnet_UTnet1Plaus``.
    source_root:
        Optional root directory that contains C, H, and A2L source files.

    Returns
    -------
    str
        Markdown-formatted DiagDocu.
    """
    dfc_info: DFCInfo | None = None
    a2l_info: A2LInfo | None = None

    if source_root is not None and source_root.is_dir():
        dfc_info = CFileParser().search_directory(source_root, dfc_name)
        a2l_info = A2LParser().search_directory(source_root, dfc_name)

    return _build_document(dfc_name, dfc_info, a2l_info)


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------

def _build_document(
    dfc_name: str,
    dfc_info: DFCInfo | None,
    a2l_info: A2LInfo | None,
) -> str:
    sections: list[str] = []

    sections.append(f"# DiagDocu: `{dfc_name}`\n")

    # ------------------------------------------------------------------
    # 1. Overview
    # ------------------------------------------------------------------
    sections.append("## 1. Übersicht\n")
    rows = [
        ("DFC-Name", f"`{dfc_name}`"),
        ("Typ", "Diagnostic Fault Code (DFC)"),
    ]
    if dfc_info and dfc_info.file_references:
        rows.append(("Quelldateien gefunden", str(len(dfc_info.file_references))))
    else:
        rows.append(("Quelldateien", "keine gefunden – Template"))

    sections.append(_table(["Attribut", "Wert"], rows))

    if dfc_info and dfc_info.comments:
        sections.append("\n### Beschreibung (aus Quellkommentaren)\n")
        for comment in dfc_info.comments[:5]:
            sections.append(f"> {comment}\n")

    # ------------------------------------------------------------------
    # 2. Input signals / context derived from C/H
    # ------------------------------------------------------------------
    sections.append("\n## 2. Eingangsgrößen\n")
    if dfc_info and dfc_info.function_signatures:
        sections.append(
            "Folgende Funktions-Signaturen wurden in den Quelldateien gefunden:\n"
        )
        sections.append("```c")
        for sig in dfc_info.function_signatures[:10]:
            sections.append(sig)
        sections.append("```\n")
    else:
        sections.append(
            "| Signal | Typ | Beschreibung |\n"
            "|--------|-----|--------------|\n"
            "| *aus Quellcode ermitteln* | – | – |\n"
        )

    # ------------------------------------------------------------------
    # 3. Fault conditions – macros / enum values
    # ------------------------------------------------------------------
    sections.append("\n## 3. Fehlerbedingungen\n")
    if dfc_info and (dfc_info.macros or dfc_info.enum_values):
        if dfc_info.macros:
            sections.append("### Makrodefinitionen\n```c")
            for macro in dfc_info.macros[:10]:
                sections.append(macro)
            sections.append("```\n")
        if dfc_info.enum_values:
            sections.append("### Enum-Werte\n```c")
            for ev in dfc_info.enum_values[:10]:
                sections.append(ev)
            sections.append("```\n")
    else:
        sections.append(
            "```c\n"
            f"/* Fehlerbedingung für {dfc_name} */\n"
            "/* bitte aus der entsprechenden C-Datei entnehmen */\n"
            "```\n"
        )

    # ------------------------------------------------------------------
    # 4. Fault storage / debouncing (template – not in C/H files directly)
    # ------------------------------------------------------------------
    sections.append("\n## 4. Fehlerspeicherung\n")
    sections.append(
        "| Parameter | Wert | Beschreibung |\n"
        "|-----------|------|--------------|\n"
        "| Debounce-Zeit | *aus A2L* | Entprellzeit für Fehlererkennung |\n"
        "| Heal-Zeit | *aus A2L* | Zeit bis Fehler als geheilt gilt |\n"
    )

    # ------------------------------------------------------------------
    # 5. Calibration parameters (from A2L)
    # ------------------------------------------------------------------
    sections.append("\n## 5. Kalibrierparameter (aus A2L)\n")
    if a2l_info and (a2l_info.measurements or a2l_info.characteristics):
        if a2l_info.measurements:
            sections.append("### Messgrößen (MEASUREMENT)\n")
            rows_m = [
                (
                    m.name,
                    m.attributes.get("DATATYPE", "–"),
                    m.attributes.get("ECU_ADDRESS", "–"),
                    m.description or "–",
                )
                for m in a2l_info.measurements[:10]
            ]
            sections.append(
                _table(["Name", "Datentyp", "ECU-Adresse", "Beschreibung"], rows_m)
            )

        if a2l_info.characteristics:
            sections.append("\n### Kalibriergrößen (CHARACTERISTIC)\n")
            rows_c = [
                (
                    c.name,
                    c.attributes.get("TYPE", c.attributes.get("DATATYPE", "–")),
                    c.description or "–",
                )
                for c in a2l_info.characteristics[:10]
            ]
            sections.append(
                _table(["Name", "Typ", "Beschreibung"], rows_c)
            )
    else:
        sections.append(
            "| Parametername | Einheit | Standardwert | Beschreibung |\n"
            "|---------------|---------|--------------|--------------|\n"
            "| *aus A2L-Datei ermitteln* | – | – | – |\n"
        )

    # ------------------------------------------------------------------
    # 6. Source code references
    # ------------------------------------------------------------------
    sections.append("\n## 6. Quellcode-Referenzen\n")
    c_refs: list[str] = []
    a2l_refs: list[str] = []

    if dfc_info:
        c_refs = dfc_info.file_references
    if a2l_info:
        a2l_refs = a2l_info.file_references

    if c_refs or a2l_refs:
        for ref in c_refs:
            sections.append(f"- `{ref}`")
        for ref in a2l_refs:
            sections.append(f"- `{ref}`")
        sections.append("")
    else:
        sections.append(
            "- **C-Datei**: `*_DFC_*.c` (Implementierung)\n"
            "- **H-Datei**: `*_DFC_*.h` (Deklaration)\n"
            "- **A2L-Datei**: Kalibrierparameter\n"
        )

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------
    sections.append("\n---\n")
    sections.append(
        f"*DiagDocu generiert von [DiagDocu\\_Agent]({_REPO_URL})*"
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _table(headers: list[str], rows: list[tuple]) -> str:
    """Return a Markdown table string."""
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    header_row = "| " + " | ".join(headers) + " |"
    data_rows = [
        "| " + " | ".join(str(c) for c in row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep] + data_rows) + "\n"
