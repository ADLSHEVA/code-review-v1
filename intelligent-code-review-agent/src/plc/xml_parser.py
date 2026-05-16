"""PLC XML parser for SimaticML / TcPOU files (Stretch Goal)."""

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from pydantic import BaseModel


class PLCProgramBlock(BaseModel):
    """A parsed PLC program block (POU)."""
    name: str
    block_type: str  # FB, FC, OB, DB
    language: str  # ST, LD, FBD, SFC
    source_code: str
    variables: list[dict] = []
    file_path: str = ""


class PLCXmlParser:
    """Parse PLC XML files to extract Structured Text code."""

    # Namespace mappings for different PLC formats
    NAMESPACES = {
        "simatic": {"ns": "http://www.siemens.com/automation"},
        "tc3": {"ns": "http://www.beckhoff.com/controls"},
    }

    @classmethod
    def parse_file(cls, file_path: str) -> PLCProgramBlock | None:
        """Parse a PLC XML file and extract the program block."""
        path = Path(file_path)
        if not path.exists():
            return None

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
        except ET.ParseError:
            return None

        # Try different PLC XML formats
        result = cls._parse_simaticml(root, file_path)
        if result is not None:
            return result

        result = cls._parse_tcpu(root, file_path)
        if result is not None:
            return result

        return None

    @classmethod
    def _parse_simaticml(cls, root: ET.Element, file_path: str) -> PLCProgramBlock | None:
        """Parse SimaticML format (TIA Portal)."""
        # Look for common SimaticML elements
        # This is a simplified parser — real SimaticML is more complex
        pou = root.find(".//{*}POU") or root.find(".//POU")
        if pou is None:
            return None

        name = pou.get("Name", "Unknown")
        block_type = pou.get("BlockType", "FB")

        # Find ST code sections
        st_sections = pou.findall(".//{*}ST") or pou.findall(".//ST")
        if not st_sections:
            return None

        source_parts = []
        for st in st_sections:
            text = ET.tostring(st, encoding="unicode", method="text")
            if text and text.strip():
                source_parts.append(text.strip())

        if not source_parts:
            return None

        return PLCProgramBlock(
            name=name,
            block_type=block_type,
            language="ST",
            source_code="\n\n".join(source_parts),
            file_path=file_path,
        )

    @classmethod
    def _parse_tcpu(cls, root: ET.Element, file_path: str) -> PLCProgramBlock | None:
        """Parse TwinCAT TcPOU format."""
        # Look for TwinCAT-specific elements
        pou = root.find(".//{*}TcPOU") or root.find(".//TcPOU")
        if pou is None:
            return None

        name_elem = pou.find("{*}Name") or pou.find("Name")
        name = name_elem.text if name_elem is not None else "Unknown"

        # Find implementation with ST language
        impl = pou.find(".//{*}Implementation") or pou.find(".//Implementation")
        if impl is None:
            return None

        st_elem = impl.find(".//{*}ST") or impl.find(".//ST")
        if st_elem is None:
            return None

        source = ET.tostring(st_elem, encoding="unicode", method="text")
        if not source or not source.strip():
            return None

        return PLCProgramBlock(
            name=name,
            block_type="FB",
            language="ST",
            source_code=source.strip(),
            file_path=file_path,
        )

    @classmethod
    def extract_st_from_xml(cls, file_path: str) -> str | None:
        """Quick helper to extract just the ST source code from a PLC XML file."""
        block = cls.parse_file(file_path)
        return block.source_code if block else None
