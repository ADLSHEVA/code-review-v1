"""PLC project file detection and source extraction helpers."""

from pathlib import Path

from .abb_parser import ABBParser
from .codesys_parser import CodesysParser
from .ge_parser import GEParser
from .hw_config import HWConfigParser
from .omron_parser import OmronParser
from .rockwell_parser import RockwellParser
from .simatic_parser import SimaticMLParser
from .twincat_parser import TwincatParser
from .xml_parser import PLCXmlParser


PLC_PROJECT_EXTENSIONS = {".xml", ".l5x", ".smc2"}


def has_plc_project_extension(file_path: str) -> bool:
    """Return True when the path has a PLC project/export extension."""
    return Path(file_path).suffix.lower() in PLC_PROJECT_EXTENSIONS


def is_plc_project_file(file_path: str) -> bool:
    """Detect known PLC XML/project exports by content."""
    suffix = Path(file_path).suffix.lower()
    if suffix == ".smc2":
        return OmronParser.is_omron(file_path)
    if suffix == ".l5x":
        return RockwellParser.is_l5x(file_path)
    if suffix != ".xml":
        return False

    detectors = (
        SimaticMLParser.is_simaticml,
        TwincatParser.is_twincat,
        CodesysParser.is_codesys,
        RockwellParser.is_l5x,
        ABBParser.is_abb,
        GEParser.is_ge,
        OmronParser.is_omron,
        HWConfigParser.is_hwconfig,
    )
    for detector in detectors:
        try:
            if detector(file_path):
                return True
        except Exception:
            continue

    try:
        block = PLCXmlParser.parse_file(file_path)
        return bool(block and block.source_code)
    except Exception:
        return False


def extract_structured_text(file_path: str) -> str | None:
    """Extract Structured Text or ST-like source from supported PLC exports."""
    suffix = Path(file_path).suffix.lower()

    extractors = []
    if suffix == ".smc2":
        extractors = [OmronParser.extract_st_from_file]
    elif suffix == ".l5x":
        extractors = [RockwellParser.extract_st_from_file]
    else:
        extractors = [
            _extract_simatic,
            TwincatParser.extract_st_from_file,
            CodesysParser.extract_st_from_file,
            RockwellParser.extract_st_from_file,
            ABBParser.extract_st_from_file,
            GEParser.extract_st_from_file,
            OmronParser.extract_st_from_file,
            _extract_generic_xml,
        ]

    for extractor in extractors:
        try:
            source = extractor(file_path)
            if source:
                return source
        except Exception:
            continue

    return None


def _extract_simatic(file_path: str) -> str | None:
    if not SimaticMLParser.is_simaticml(file_path):
        return None

    block = SimaticMLParser.parse_file(file_path)
    if not block:
        return None
    if block.source_code:
        return block.source_code

    parts = [network.source_code for network in block.networks if network.source_code]
    return "\n\n".join(parts) if parts else None


def _extract_generic_xml(file_path: str) -> str | None:
    block = PLCXmlParser.parse_file(file_path)
    if block and block.source_code:
        return block.source_code
    return None
