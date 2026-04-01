"""Parser for C and H source files to extract DFC-related information."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DFCInfo:
    """Extracted information about a Diagnostic Fault Code from C/H sources."""

    name: str
    file_references: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    macros: list[str] = field(default_factory=list)
    function_signatures: list[str] = field(default_factory=list)
    enum_values: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)


class CFileParser:
    """Parser for C and H source files.

    Searches for DFC-related definitions, declarations, and usages
    within C and H files to populate a :class:`DFCInfo` object.
    """

    # A block comment immediately before a definition
    _BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
    # A line comment
    _LINE_COMMENT_RE = re.compile(r"//[^\n]*")
    # #include directives
    _INCLUDE_RE = re.compile(r'#\s*include\s+["<]([^">]+)[">]')
    # #define lines that mention the DFC name (filled in per call)
    _MACRO_RE_TEMPLATE = r"(#\s*define\s+[^\n]*{name}[^\n]*)"
    # Enum value lines: leading whitespace, identifier starting with DFC name, optional = value, comma
    # Uses (?m) multiline so ^ anchors to the start of each line.
    _ENUM_RE_TEMPLATE = r"(?m)^(\s+{name}\w*\s*(?:=\s*[^,\n]+)?,?)"
    # Function signature lines: return-type DFC_name[suffix]( params )
    # Uses (?m) multiline so ^ anchors to the start of each line, which
    # avoids matching #define lines that happen to contain parentheses.
    _FUNC_SIG_RE_TEMPLATE = r"(?m)^[\w][\w\s\*]*\b{name}\w*\s*\([^)]*\)"

    def parse_file(self, filepath: Path, dfc_name: str) -> DFCInfo:
        """Parse *filepath* and extract information relevant to *dfc_name*.

        Parameters
        ----------
        filepath:
            Absolute or relative path to a ``.c`` or ``.h`` file.
        dfc_name:
            The DFC identifier to search for, e.g. ``DFC_rbe_CddUTnet_UTnet1Plaus``.

        Returns
        -------
        DFCInfo
            Populated with whatever information could be extracted.
        """
        info = DFCInfo(name=dfc_name)
        source = filepath.read_text(encoding="utf-8", errors="replace")
        escaped = re.escape(dfc_name)

        # Quick check – skip files that don't mention the DFC at all
        if dfc_name not in source:
            return info

        info.file_references.append(str(filepath))

        # --- includes -------------------------------------------------------
        info.includes = self._INCLUDE_RE.findall(source)

        # --- macros ---------------------------------------------------------
        macro_re = re.compile(self._MACRO_RE_TEMPLATE.format(name=escaped))
        info.macros = [m.strip() for m in macro_re.findall(source)]

        # --- function signatures --------------------------------------------
        func_re = re.compile(self._FUNC_SIG_RE_TEMPLATE.format(name=escaped))
        info.function_signatures = [f.strip() for f in func_re.findall(source)]

        # --- enum values ----------------------------------------------------
        enum_re = re.compile(self._ENUM_RE_TEMPLATE.format(name=escaped))
        info.enum_values = [e.strip() for e in enum_re.findall(source)]

        # --- comments preceding or surrounding the DFC name -----------------
        for m in self._BLOCK_COMMENT_RE.finditer(source):
            # Keep block comments that directly mention the DFC
            if dfc_name in m.group():
                info.comments.append(m.group().strip())

        for m in self._LINE_COMMENT_RE.finditer(source):
            if dfc_name in m.group():
                info.comments.append(m.group().strip())

        # Deduplicate while preserving order
        info.comments = list(dict.fromkeys(info.comments))
        info.macros = list(dict.fromkeys(info.macros))
        info.function_signatures = list(dict.fromkeys(info.function_signatures))
        info.enum_values = list(dict.fromkeys(info.enum_values))

        return info

    def search_directory(
        self,
        directory: Path,
        dfc_name: str,
        extensions: tuple[str, ...] = (".c", ".h"),
    ) -> DFCInfo:
        """Recursively search *directory* for files referencing *dfc_name*.

        All matching information from individual files is merged into a single
        :class:`DFCInfo` object.

        Parameters
        ----------
        directory:
            Root directory to search.
        dfc_name:
            The DFC identifier to search for.
        extensions:
            File extensions to consider (default: ``.c`` and ``.h``).

        Returns
        -------
        DFCInfo
            Merged information from all matching files.
        """
        merged = DFCInfo(name=dfc_name)
        for filepath in directory.rglob("*"):
            if filepath.suffix.lower() not in extensions:
                continue
            result = self.parse_file(filepath, dfc_name)
            merged.file_references.extend(result.file_references)
            merged.comments.extend(result.comments)
            merged.macros.extend(result.macros)
            merged.function_signatures.extend(result.function_signatures)
            merged.enum_values.extend(result.enum_values)
            merged.includes.extend(result.includes)

        # Deduplicate
        merged.file_references = list(dict.fromkeys(merged.file_references))
        merged.comments = list(dict.fromkeys(merged.comments))
        merged.macros = list(dict.fromkeys(merged.macros))
        merged.function_signatures = list(dict.fromkeys(merged.function_signatures))
        merged.enum_values = list(dict.fromkeys(merged.enum_values))
        merged.includes = list(dict.fromkeys(merged.includes))

        return merged
