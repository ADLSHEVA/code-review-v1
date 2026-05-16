# PLC Extension Design

## Overview

The PLC extension provides deep analysis of IEC 61131-3 Structured Text (ST) code and PLC project files from 7 major industrial automation vendors. It combines static analysis (30+ rules, CFG analysis, external tools) with LLM-based semantic review.

## Supported Vendors

| Vendor | Format | Parser | Extensions |
|--------|--------|--------|------------|
| **Siemens** (TIA Portal) | SimaticML XML | `SimaticMLParser` | `.xml` |
| **Beckhoff** (TwinCAT 3) | TcPOU XML (CDATA) | `TwincatParser` | `.xml` |
| **CODESYS** (WAGO, Schneider, ABB AC500, Bosch Rexroth, Phoenix Contact) | CODESYS V3 XML | `CodesysParser` | `.xml` |
| **Rockwell** (Studio 5000) | L5X XML | `RockwellParser` | `.xml`, `.l5x` |
| **ABB** (Automation Builder) | ABB XML / CODESYS | `ABBParser` | `.xml` |
| **GE/Fanuc** (Proficy Machine Edition) | GE XML | `GEParser` | `.xml` |
| **Omron** (Sysmac Studio) | .smc2 ZIP/XML | `OmronParser` | `.smc2`, `.xml` |

Parsers are tried in auto-detection order: `SimaticML → TwinCAT → CODESYS → Rockwell → ABB → GE → Omron → Generic`

## Components

### Vendor Parsers (`src/plc/`)

Each parser extracts POUs (Program Organization Units), variables, and ST source code from vendor-specific XML formats:

- `simatic_parser.py` — Siemens SimaticML (SCL, LAD, FBD blocks)
- `twincat_parser.py` — Beckhoff TcPOU (CDATA-wrapped ST/LD/FBD/SFC)
- `codesys_parser.py` — CODESYS V3 (WAGO, Schneider, ABB AC500, etc.)
- `rockwell_parser.py` — Rockwell L5X (ST/RLL, Tag definitions)
- `abb_parser.py` — ABB Automation Builder (CODESYS-compatible)
- `ge_parser.py` — GE/Fanuc Proficy Machine Edition
- `omron_parser.py` — Omron Sysmac Studio (.smc2 ZIP extraction)
- `xml_parser.py` — Generic PLC XML fallback

### Graphical Language Converters

Convert graphical PLC languages to Structured Text for analysis:

- `ld_converter.py` — **Ladder Diagram → ST** via AOV graph + topological sort
- `fbd_converter.py` — **Function Block Diagram → ST** via dependency graph + Kahn's sort
- `sfc_converter.py` — **Sequential Function Chart → ST** via CASE-based state machine

### ST Extractor (`src/plc/st_extractor.py`)

Extracts and parses ST constructs:
- Function blocks (FUNCTION_BLOCK), Functions (FUNCTION), Programs (PROGRAM)
- Variable declarations (VAR, VAR_INPUT, VAR_OUTPUT, VAR_GLOBAL, VAR CONSTANT)
- Structured types (TYPE ... END_TYPE)

### Rule Checker (`src/plc/plc_rules.py`)

30+ rules across 3 levels:

**Level 1 — Pattern-based (regex):**
PLC-001 (direct I/O), PLC-003 (magic numbers), PLC-005 (unsafe conversion), PLC-006 (division by zero), PLC-010 (unsafe string ops), PLC-011 (float equality), PLC-012 (pointer dereference), PLC-020 (GOTO), PLC-021 (empty branch), PLC-022 (EXIT in loop), PLC-025 (RETURN in PROGRAM)

**Level 2 — Structural analysis:**
PLC-002 (missing watchdog), PLC-004 (array bounds), PLC-013 (naming convention), PLC-014 (no initial value), PLC-015 (block >200 lines), PLC-016 (I/O missing comment), PLC-023 (nesting >4 levels), PLC-024 (unused variable)

**Level 3 — Semantic analysis:**
PLC-007 (no interlock), PLC-008 (race condition), PLC-009 (no E-Stop), PLC-017 (no range validation), PLC-018 (no timeout), PLC-019 (no fail-safe default)

### CFG Analyzer (`src/plc/cfg_analyzer.py`)

Builds control flow graphs from ST code:
- CFG-001: Unreachable code detection
- CFG-002: Infinite loop detection
- CFG-003: Used-before-defined (def-use chain)
- CFG-004: Dead store detection
- CFG-005: High cyclomatic complexity (>15)

### External Tool Integration (`src/plc/external_analyzer.py`)

Adapters for external PLC static analysis tools (auto-detected):
- **IEC Checker** — IEC 61131-3 compliance, type checking, dead code
- **plc-lint** — Lightweight ST linter
- **Custom tools** — Any tool with line-based output format

### Hardware Config Verifier (`src/plc/hw_config.py`)

Parses and validates TIA Portal hardware configuration XML:
- CPU model, firmware, protection level, watchdog, web server, OPC-UA
- I/O modules: type, slot, addresses, safety/redundancy flags
- Network: protocol, IP, PROFINET DCP, port security, encryption
- 12 validation rules (HW-001 through HW-012)

### Fine-tuning Pipeline (`src/plc/finetune/`)

Generates training datasets for PLC-specialized LLM fine-tuning:
- `domain_context.py` — IEC 61131-3 knowledge base (20+ CWE patterns, PLCopen guidelines)
- `prompt_builder.py` — PLC-specialized prompts (safety, chain-of-thought, vulnerability)
- `dataset_generator.py` — Training data generation from rules + codebase scans
- `cli.py` — CLI entry point for JSONL/Alpaca/ShareGPT export

## RAG Knowledge Base

The PLC extension indexes additional guidelines:
- PLCopen coding guidelines
- Secure PLC Coding Practices (ISA/IEC 62443)

## Limitations

- Tree-sitter grammar for ST is not available — uses regex-based parsing for ST constructs
- Hardware config verification only supports Siemens TIA Portal HWConfig XML
- CODESYS ZIP archives must be extracted before review (Omron .smc2 is auto-extracted)
