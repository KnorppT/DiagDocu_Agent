"""Parser for ASAP2 (A2L) calibration description files.

A2L files use a hierarchical block syntax::

    /begin MEASUREMENT MeasurementName "Short Description"
        DATATYPE UBYTE
        ECU_ADDRESS 0x1234
        ...
    /end MEASUREMENT

This parser extracts MEASUREMENT and CHARACTERISTIC blocks that are
related to a given DFC name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class A2LObject:
    """Represents a single MEASUREMENT or CHARACTERISTIC from an A2L file."""

    block_type: str  # "MEASUREMENT" or "CHARACTERISTIC"
    name: str
    description: str
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class A2LInfo:
    """Extracted A2L information relevant to a DFC."""

    dfc_name: str
    measurements: list[A2LObject] = field(default_factory=list)
    characteristics: list[A2LObject] = field(default_factory=list)
    file_references: list[str] = field(default_factory=list)


class A2LParser:
    """Parser for ASAP2 (A2L) calibration description files.

    Supports extracting ``MEASUREMENT`` and ``CHARACTERISTIC`` objects
    whose names contain parts of a DFC identifier.
    """

    # Matches /begin BLOCK_TYPE Name "Description" ... /end BLOCK_TYPE
    _BLOCK_RE = re.compile(
        r"/begin\s+(MEASUREMENT|CHARACTERISTIC)\s+"
        r"(\w+)\s+"
        r'"([^"]*)"\s*'
        r"(.*?)"
        r"/end\s+\1",
        re.DOTALL,
    )

    # Generic key-value attribute inside a block (e.g. "DATATYPE UBYTE")
    _ATTR_RE = re.compile(r"^\s*(\w+)\s+(.+?)\s*$", re.MULTILINE)

    def parse_file(self, filepath: Path, dfc_name: str) -> A2LInfo:
        """Parse *filepath* and return A2L objects related to *dfc_name*.

        The parser searches for MEASUREMENT and CHARACTERISTIC blocks whose
        names share at least one meaningful token with *dfc_name*.

        Parameters
        ----------
        filepath:
            Path to the ``.a2l`` file.
        dfc_name:
            The DFC identifier, e.g. ``DFC_rbe_CddUTnet_UTnet1Plaus``.

        Returns
        -------
        A2LInfo
        """
        info = A2LInfo(dfc_name=dfc_name)
        source = filepath.read_text(encoding="utf-8", errors="replace")

        # Build a set of tokens from the DFC name for fuzzy matching
        tokens = self._dfc_tokens(dfc_name)

        for match in self._BLOCK_RE.finditer(source):
            block_type = match.group(1)
            name = match.group(2)
            description = match.group(3)
            body = match.group(4)

            if not self._name_is_relevant(name, tokens):
                continue

            obj = A2LObject(
                block_type=block_type,
                name=name,
                description=description,
                attributes=self._parse_attributes(body),
            )

            if block_type == "MEASUREMENT":
                info.measurements.append(obj)
            else:
                info.characteristics.append(obj)

        if info.measurements or info.characteristics:
            info.file_references.append(str(filepath))

        return info

    def search_directory(self, directory: Path, dfc_name: str) -> A2LInfo:
        """Recursively search *directory* for A2L files related to *dfc_name*.

        Parameters
        ----------
        directory:
            Root directory to search.
        dfc_name:
            The DFC identifier to search for.

        Returns
        -------
        A2LInfo
            Merged information from all matching A2L files.
        """
        merged = A2LInfo(dfc_name=dfc_name)
        for filepath in directory.rglob("*.a2l"):
            result = self.parse_file(filepath, dfc_name)
            merged.measurements.extend(result.measurements)
            merged.characteristics.extend(result.characteristics)
            merged.file_references.extend(result.file_references)

        merged.file_references = list(dict.fromkeys(merged.file_references))
        return merged

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dfc_tokens(dfc_name: str) -> set[str]:
        """Return lower-case tokens from a DFC name, ignoring the ``DFC`` prefix."""
        parts = re.split(r"[_\s]+", dfc_name)
        # Drop the leading "DFC" and very short tokens
        return {p.lower() for p in parts if len(p) > 1 and p.upper() != "DFC"}

    @staticmethod
    def _name_is_relevant(a2l_name: str, tokens: set[str]) -> bool:
        """Return True when *a2l_name* shares at least one token with *tokens*."""
        name_lower = a2l_name.lower()
        return any(t in name_lower for t in tokens)

    def _parse_attributes(self, body: str) -> dict[str, str]:
        """Extract simple key-value attributes from a block body."""
        attrs: dict[str, str] = {}
        for m in self._ATTR_RE.finditer(body):
            key = m.group(1)
            value = m.group(2).strip().strip('"')
            # Skip sub-block keywords
            if key.upper() in {"BEGIN", "END"}:
                continue
            attrs[key] = value
        return attrs
