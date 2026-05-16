# Intelligent Code Review Agent

AI-powered code review agent with **deep industrial PLC/ICS support**. Reviews code changes using both static analysis and LLM-based reasoning, covering 7 PLC vendors, 3 graphical language converters, 30+ security/safety rules, control flow analysis, hardware configuration verification, and an LLM fine-tuning data pipeline.

## Table of Contents

- [Quick Start](#quick-start)
- [Step-by-Step Usage Examples](#step-by-step-usage-examples)
- [Web GUI](#web-gui)
  - [Dashboard](#dashboard)
  - [New Scan](#new-scan)
  - [File Scan (Drag & Drop)](#file-scan-drag--drop)
  - [Report Viewer](#report-viewer)
  - [Compare Reports](#compare-reports)
  - [Guidelines Management](#guidelines-management)
  - [Settings](#settings)
- [Deployment](#deployment)
  - [Backend (FastAPI)](#backend-fastapi)
  - [Frontend (Vue 3)](#frontend-vue-3)
  - [Production Build](#production-build)
- [Model Configuration](#model-configuration)
  - [Switching Models](#switching-models)
  - [Custom API Endpoints (Mimo, etc.)](#custom-api-endpoints-mimo-etc)
  - [Supported Model IDs](#supported-model-ids)
- [Architecture](#architecture)
- [PLC Vendor Support (7 parsers)](#plc-vendor-support-7-parsers)
- [Graphical Language Converters (3 converters)](#graphical-language-converters-3-converters)
- [Rule Checker (30+ rules, 3 levels)](#rule-checker-30-rules-3-levels)
- [Control Flow Graph Analysis](#control-flow-graph-analysis)
- [External Tool Integration](#external-tool-integration)
- [Hardware Configuration Verification](#hardware-configuration-verification)
- [LLM Fine-tuning Data Pipeline](#llm-fine-tuning-data-pipeline)
- [Supported Languages (28)](#supported-languages-28)
- [Project Structure](#project-structure)
- [Configuration Reference](#configuration-reference)
- [Testing](#testing)
- [Market Coverage](#market-coverage)
- [FAQ](#faq)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Anthropic API key (or compatible endpoint)

### Installation

```bash
pip install -e .
# or
pip install langchain-anthropic langchain-core pydantic-settings chromadb sentence-transformers
```

### Configuration

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-20250514
# For custom endpoints (e.g., Mimo):
# ANTHROPIC_BASE_URL=https://your-endpoint.com/v1
# DISABLE_THINKING=true
```

### Run

```bash
# Review a git diff
python -m src.cli review --repo /path/to/repo

# Review a single file
python -m src.cli review-file --path code.st

# Generate fine-tuning dataset
python -m src.plc.finetune.cli --output ./data/training.jsonl
```

---

## Step-by-Step Usage Examples

### Example 1: Review a Git Commit

Suppose you have a PLC project at `D:\MyPLCProject` and want to review the latest commit:

```bash
# Step 1: Navigate to the agent directory
cd "D:\intelligent-code-review-agent"

# Step 2: Run the review on HEAD commit
python -m src.main "D:\MyPLCProject" --commit HEAD

# Step 3: Output as JSON and save to file
python -m src.main "D:\MyPLCProject" --commit HEAD --format json -o review.json

# Review a specific commit by hash
python -m src.main "D:\MyPLCProject" --commit abc1234

# Use a specific model
python -m src.main "D:\MyPLCProject" --commit HEAD --model claude-opus-4-7
```

**Sample output:**

```
Found 5 changed files, +120 -30 lines
Running AI review...

Code Review Report
==================

Found 8 issue(s): 2 critical, 3 errors, 2 warnings, 1 info.

## D:\MyPLCProject\MotorControl.st

### [CRITICAL] PLC-006: Division without zero check
Line 45: Result := Speed / Divisor;  // Divisor not checked for zero
Suggestion: Add IF ABS(Divisor) > 0.001 THEN ... END_IF;

### [ERROR] PLC-009: Missing emergency stop handling
Line 12: Motor := StartButton AND NOT StopButton;  // No E-Stop check
Suggestion: Add EStop signal check

### [WARNING] PLC-003: Magic number
Line 23: IF Speed > 1500 THEN  // What does 1500 mean?
Suggestion: Define constant VAR CONSTANT MAX_SPEED : INT := 1500;
```

### Example 2: Review Branch Differences

```bash
# Compare main branch vs feature branch
python -m src.main "D:\MyPLCProject" --base main --head feature/new-motor

# Compare two tags
python -m src.main "D:\MyPLCProject" --base v1.0 --head v1.1

# Save comparison result as JSON
python -m src.main "D:\MyPLCProject" --base main --head develop --format json -o diff_review.json
```

### Example 3: Review a PLC Project

PLC project review works exactly the same way -- the tool automatically detects PLC files and runs deep analysis:

```bash
# Review a TIA Portal project
python -m src.main "D:\TIA_Project" --commit HEAD

# Review a TwinCAT 3 project
python -m src.main "D:\TwinCAT_Project" --commit HEAD

# Review a CODESYS project (WAGO, Schneider, ABB AC500, etc.)
python -m src.main "D:\CodesysProject" --commit HEAD

# Review a Rockwell Studio 5000 L5X export
python -m src.main "D:\Studio5000_Project" --commit HEAD
```

**PLC review automatically performs these analyses:**

1. **Vendor parsing** -- Auto-detects XML format (Siemens / Beckhoff / CODESYS / Rockwell / ABB / GE / Omron)
2. **Graphical language conversion** -- LD / FBD / SFC auto-converted to ST
3. **30+ rule checks** -- Pattern matching + structural analysis + semantic analysis
4. **Control flow analysis** -- Unreachable code, infinite loops, uninitialized variables, dead stores
5. **External tools** -- Auto-detects and runs installed IEC Checker, plc-lint
6. **Hardware config** -- TIA Portal HWConfig XML auto-validated
7. **LLM review** -- AI deep semantic analysis with domain-aware prompts

### Example 4: Generate LLM Fine-tuning Data

```bash
# Generate from rules + vulnerability database
python -m src.plc.finetune.cli --output ./data/training.jsonl

# Generate from a real PLC codebase (runs rule checker + CFG analyzer)
python -m src.plc.finetune.cli --repo "D:\MyPLCProject" --output ./data/training.jsonl

# Export in Alpaca format with automatic train/val/test split
python -m src.plc.finetune.cli --format alpaca --split --output-dir ./data/

# Export in ShareGPT format
python -m src.plc.finetune.cli --format sharegpt --output ./data/sharegpt.json

# Print dataset statistics
python -m src.plc.finetune.cli --stats
```

**Output format details:**

| Format | Use Case | File Structure |
|--------|----------|----------------|
| JSONL | OpenAI / Anthropic fine-tuning | `{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}` |
| Alpaca | LLaMA-family fine-tuning | `{"instruction": "...", "input": "...", "output": "..."}` |
| ShareGPT | Multi-turn conversation fine-tuning | `{"conversations": [{"from": "human", ...}, {"from": "gpt", ...}]}` |

---

## Web GUI

The project includes a full-featured web interface built with **Vue 3 + TypeScript + Pinia**. It provides a visual way to run scans, view reports, manage guidelines, and configure the system.

### Starting the Web GUI

```bash
# Terminal 1: Start the backend API
cd "D:\intelligent-code-review-agent"
py -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Start the frontend dev server
cd web
npm install
npm run dev
# Open http://localhost:5174
```

### Dashboard

The home page (`/`) displays all past scan reports grouped by repository folder. Each report card shows:

- **Repository path** and scan timestamp
- **Issue severity breakdown** (Critical / Error / Warning / Info) as colored badges
- **Summary** of the review findings
- Click any report card to view the full report

### New Scan

The scan page (`/scan`) provides two modes:

**Single Commit Mode** — Review changes in a specific commit:
- Enter the repository path (e.g., `D:\MyProject`)
- Enter a commit SHA or `HEAD` for the latest commit
- Click "Start Scan"

**Branch Diff Mode** — Compare two branches:
- Enter the repository path
- Set Base ref (default: `main`) and Head ref (default: `develop`)
- Click "Start Scan"

**RAG Panel** — The right sidebar shows the current RAG knowledge base status:
- Number of default guideline files (3 built-in)
- Number of custom uploaded guideline files
- Total indexed chunks for vector search
- Link to manage guidelines

**Progress Tracking** — During a scan, a live progress bar shows:
- Current progress percentage
- Number of files processed / total
- Currently scanning file path
- Elapsed time

### File Scan (Drag & Drop)

The file scan page (`/file-scan`) allows scanning a single code file without needing a git repository:

1. **Drag and drop** a code file onto the drop zone, or click to browse
2. The system auto-detects the programming language from the file extension
3. A language badge shows the detected language (or "Unsupported" if not recognized)
4. Click **"Scan"** to start the vulnerability analysis
5. On completion, you're automatically redirected to the report page

Supported file types: All 28 supported languages (see [Supported Languages](#supported-languages-28)).

### Report Viewer

The report page (`/report/:id`) displays the full review results:

- **Summary** — High-level findings overview
- **Issue List** — All findings sorted by severity (Critical → Error → Warning → Info)
- Each issue shows: file path, line range, category, title, description, and fix suggestion
- **Filtering** — Filter by severity level or category
- **File Coverage** — List of reviewed and skipped files

### Compare Reports

The compare page (`/compare`) allows side-by-side comparison of two scan reports:

- Select two reports from dropdown menus
- See differences in issue counts, severity distribution, and new/resolved issues
- Useful for tracking code quality improvements between commits

### Guidelines Management

The guidelines page (`/guidelines`) manages the RAG knowledge base:

- **Upload** custom guideline files (`.md`, `.txt`, `.rst`, `.adoc`, `.pdf`, `.docx`)
- **View** all uploaded guideline files with chunk counts
- **Delete** individual guideline files
- **Reindex** the vector store after changes
- Uploaded guidelines are automatically chunked and indexed for vector search

### Settings

The settings page (`/settings`) displays the current configuration:

- **Model** — Currently configured LLM model
- **API Endpoint** — Base URL for the API
- **Supported Languages** — Full list of 28 supported programming languages with their file extensions
- **Review Parameters** — Confidence threshold, max context tokens, temperature

---

## Deployment

### Backend (FastAPI)

```bash
# Install Python dependencies
cd "D:\intelligent-code-review-agent"
pip install -e .

# Start the API server (development)
py -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Start the API server (production)
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API server provides:
- `POST /api/scan/start` — Start a new scan job
- `GET /api/scan/status/{job_id}` — Poll scan progress
- `GET /api/scan/reports` — List all reports
- `GET /api/report/{id}` — Get a specific report
- `POST /api/file-scan/` — Scan a single uploaded file
- `GET /api/guidelines/list` — List guideline files
- `POST /api/guidelines/upload` — Upload a guideline file
- `GET /api/health` — Health check endpoint

### Frontend (Vue 3)

```bash
cd web

# Install dependencies
npm install

# Development server (with hot reload)
npm run dev
# Runs on http://localhost:5174, proxies /api to backend

# Type checking
npm run type-check

# Linting
npm run lint
```

### Production Build

```bash
# Build the frontend
cd web
npm run build

# The built files are in web/dist/
# The backend serves them automatically via StaticFiles mount
# Just start the backend and open http://localhost:8000
py -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

**Architecture in production:**
- The FastAPI backend serves the built Vue SPA from `web/dist/`
- All `/api/*` routes are handled by the backend
- All other routes fall through to `index.html` (client-side routing)
- No separate web server (nginx, etc.) needed

---

## Model Configuration

### Switching Models

Edit the `.env` file in the project root to change the LLM model:

```env
# Use Claude Sonnet (default, recommended for most use cases)
CLAUDE_MODEL=claude-sonnet-4-20250514

# Use Claude Opus (highest quality, slower)
CLAUDE_MODEL=claude-opus-4-7

# Use Claude Haiku (fastest, lower quality)
CLAUDE_MODEL=claude-haiku-4-5-20251001
```

After changing the `.env` file, restart the backend server for changes to take effect.

### Custom API Endpoints (Mimo, etc.)

To use a compatible API endpoint (e.g., Mimo, OpenRouter, or a self-hosted proxy):

```env
# Point to your custom endpoint
ANTHROPIC_BASE_URL=https://your-endpoint.com/v1
ANTHROPIC_API_KEY=your-api-key-here

# For reasoning models that don't support extended thinking
DISABLE_THINKING=true
```

**Important notes:**
- The `DISABLE_THINKING=true` flag is required for Mimo and other reasoning models that don't support Claude's extended thinking feature
- Custom endpoints must be compatible with the Anthropic Messages API format
- The `ANTHROPIC_API_KEY` is sent as the `x-api-key` header

### Supported Model IDs

| Model | ID | Best For |
|-------|-----|----------|
| Claude Sonnet 4 | `claude-sonnet-4-20250514` | Default, balanced speed/quality |
| Claude Opus 4 | `claude-opus-4-7` | Highest quality analysis |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | Fastest, good for simple reviews |

You can also use any model ID supported by your custom endpoint.

---

## Supported Languages (28)

The agent supports 28 programming languages with Tree-sitter AST parsing for deep context extraction:

| Language | Extensions | AST Support |
|----------|-----------|-------------|
| Python | `.py` | Tree-sitter |
| JavaScript | `.js`, `.jsx` | Tree-sitter |
| TypeScript | `.ts`, `.tsx` | Tree-sitter |
| Java | `.java` | Tree-sitter |
| Go | `.go` | Tree-sitter |
| Rust | `.rs` | Tree-sitter |
| C | `.c`, `.h` | Tree-sitter |
| C++ | `.cpp`, `.hpp` | Tree-sitter |
| C# | `.cs` | Tree-sitter |
| PHP | `.php` | Tree-sitter |
| Ruby | `.rb` | Tree-sitter |
| Swift | `.swift` | Tree-sitter |
| Kotlin | `.kt`, `.kts` | Tree-sitter |
| Scala | `.scala`, `.sc` | Tree-sitter |
| Lua | `.lua` | Tree-sitter |
| SQL | `.sql` | Tree-sitter |
| Julia | `.jl` | Tree-sitter |
| MATLAB | `.m` | Tree-sitter |
| Solidity | `.sol` | Tree-sitter |
| Shell/Bash | `.sh`, `.bash`, `.zsh` | Tree-sitter |
| Verilog/SystemVerilog | `.v`, `.vh`, `.sv`, `.svh` | Tree-sitter |
| Zig | `.zig` | Tree-sitter |
| Objective-C | `.mm` | Tree-sitter |
| Dart | `.dart` | LLM only |
| Structured Text (PLC) | `.st`, `.iecst` | LLM only |
| COBOL | `.cob`, `.cbl`, `.cpy` | LLM only |
| R | `.r` | LLM only |
| SAS | `.sas` | LLM only |

**AST Support** means the agent uses Tree-sitter to extract enclosing functions, classes, imports, and related symbols around changed lines. Languages marked "LLM only" still get full LLM-based review — the agent sends the complete source code and diff to the model.

---

## Architecture

```
+-----------------------------------------------------------------+
|                    Code Review Agent                            |
|  +----------+  +----------+  +----------+  +--------------+    |
|  |   Git    |  |  Parser  |  |   RAG    |  |   LLM        |    |
|  |   Diff   |->| Context  |->|Retriever |->| (Claude/Mimo)|    |
|  |  Reader  |  | Builder  |  |(ChromaDB)|  |              |    |
|  +----------+  +----------+  +----------+  +--------------+    |
|                      |                            |             |
|                      v                            v             |
|  +------------------------------------------------------------+|
|  |                  PLC Analysis Pipeline                     ||
|  |                                                           ||
|  |  +-------------+  +----------+  +-------------------+     ||
|  |  |   Vendor    |  |Graphical |  |  Core Analysis    |     ||
|  |  |   Parsers   |->|Converters|->|                   |     ||
|  |  |  (7 types)  |  | (LD/FBD/ |  | PLC Rules (30+)   |     ||
|  |  |             |  |  SFC->ST) |  | CFG Analyzer       |     ||
|  |  |             |  |          |  | External Tools     |     ||
|  |  |             |  |          |  | HW Config Verifier |     ||
|  |  +-------------+  +----------+  +-------------------+     ||
|  +------------------------------------------------------------+|
|                              |                                  |
|                              v                                  |
|                    +------------------+                        |
|                    |  Review Comments |                        |
|                    |  (deduplicated,  |                        |
|                    |   sorted)        |                        |
|                    +------------------+                        |
+-----------------------------------------------------------------+
```

### Dual Analysis Pipeline

Every PLC file gets two independent analyses that are merged and deduplicated:

1. **Static Analysis** -- Pattern rules, structural checks, CFG analysis, external tools
2. **LLM Analysis** -- Claude/Mimo with domain-aware prompts and RAG context

---

## PLC Vendor Support (7 parsers)

| Vendor | Format | Parser | File Extensions |
|--------|--------|--------|-----------------|
| **Siemens** (TIA Portal) | SimaticML XML | `SimaticMLParser` | `.xml` |
| **Beckhoff** (TwinCAT 3) | TcPOU XML (CDATA) | `TwincatParser` | `.xml` |
| **CODESYS** (WAGO, Schneider, ABB AC500, Bosch Rexroth, Phoenix Contact) | CODESYS V3 XML | `CodesysParser` | `.xml` |
| **Rockwell** (Studio 5000) | L5X XML | `RockwellParser` | `.xml`, `.l5x` |
| **ABB** (Automation Builder) | ABB XML / CODESYS | `ABBParser` | `.xml` |
| **GE/Fanuc** (Proficy Machine Edition) | GE XML | `GEParser` | `.xml` |
| **Omron** (Sysmac Studio) | .smc2 ZIP/XML | `OmronParser` | `.smc2`, `.xml` |

Each parser follows the same API:

```python
from src.plc import SimaticMLParser, TwincatParser, CodesysParser

# --- Siemens TIA Portal ---
if SimaticMLParser.is_simaticml("project.xml"):
    block = SimaticMLParser.parse_file("project.xml")
    print(f"Block: {block.name}")
    print(f"Type: {block.block_type}")           # FC, FB, OB, DB
    print(f"Language: {block.programming_language}")  # SCL, LAD, FBD
    print(f"ST code:\n{block.source_code}")
    for var in block.variables:
        print(f"  Variable: {var.name} : {var.datatype} ({var.scope})")

# --- Beckhoff TwinCAT 3 ---
if TwincatParser.is_twincat("TcPOU.xml"):
    project = TwincatParser.parse_file("TcPOU.xml")
    for pou in project.pous:
        print(f"POU: {pou.name} ({pou.pou_type})")
        print(f"Implementation:\n{pou.implementation}")

# --- CODESYS (WAGO, Schneider, ABB AC500, etc.) ---
if CodesysParser.is_codesys("project.xml"):
    project = CodesysParser.parse_file("project.xml")
    for pou in project.all_pous:
        print(f"{pou.pou_type} {pou.name} [{pou.language}]")
```

### Parser Chain (auto-detection)

When an XML file is encountered, parsers are tried in order:

```
SimaticML -> TwinCAT -> CODESYS -> Rockwell -> ABB -> GE -> Omron -> Generic
```

The first parser that matches the XML structure is used.

---

## Graphical Language Converters (3 converters)

### Ladder Diagram -> ST (`LadderDiagramConverter`)

```python
from src.plc import LadderDiagramConverter

source = open("program.st").read()
if LadderDiagramConverter.has_graphical_language(source):
    result = LadderDiagramConverter.extract_and_convert(source)
    print(result.st_code)
```

Converts LD relay logic to ST via AOV graph + topological sort:

| LD Element | ST Equivalent |
|------------|---------------|
| NO contact | `AND variable` |
| NC contact | `AND NOT variable` |
| Coil | Assignment (`:=`) |
| Parallel branches | `OR` logic |
| TON/TOF/TP | Timer FB call |
| CTU/CTD/CTUD | Counter FB call |

### Function Block Diagram -> ST (`FBDConverter`)

```python
from src.plc import FBDConverter

if FBDConverter.has_fbd_marker(source):
    result = FBDConverter.extract_and_convert(source)
    print(result.st_code)
```

Converts FBD data flow to ST via dependency graph + Kahn's topological sort:

| FBD Block | ST Equivalent |
|-----------|---------------|
| AND, OR, XOR, NOT | Boolean operators |
| ADD, SUB, MUL, DIV, MOD | Arithmetic operators |
| GT, GE, LT, LE, EQ, NE | Comparison operators |
| MOVE | Assignment |
| SEL, MAX, MIN, LIMIT | Selection functions |
| SHL, SHR, ROL, ROR | Bit operations |
| INT_TO_REAL, etc. | Type conversion calls |
| TON, TOF, TP | Timer FB calls |
| CTU, CTD, CTUD | Counter FB calls |
| SR, RS | Latch FB calls |
| R_TRIG, F_TRIG | Edge detection FB calls |

### Sequential Function Chart -> ST (`SFCConverter`)

```python
from src.plc import SFCConverter

if SFCConverter.has_sfc_marker(source):
    result = SFCConverter.extract_and_convert(source)
    print(result.st_code)  # CASE-based state machine
```

Converts SFC state machines to ST CASE-based logic:

- Steps -> `E_Step` enum type
- Transitions -> IF conditions
- Actions -> CASE branches with action qualifiers (N, P, S, R, L, D, P1, P0)
- Divergence/Convergence -> Parallel/alternative branch logic

---

## Rule Checker (30+ rules, 3 levels)

### Level 1 -- Pattern-based (regex)

| Rule | Description | Severity |
|------|-------------|----------|
| PLC-001 | Direct I/O address in program body | warning |
| PLC-003 | Hardcoded magic number | warning |
| PLC-005 | Unsafe type conversion | info |
| PLC-006 | Division without zero check | error |
| PLC-010 | Unsafe string operation | warning |
| PLC-011 | Floating point equality comparison | warning |
| PLC-012 | Pointer dereference without nil check | error |
| PLC-020 | GOTO statement usage | warning |
| PLC-021 | Empty control block branch | info |
| PLC-022 | EXIT statement in loop | info |
| PLC-025 | RETURN in PROGRAM block | warning |

### Level 2 -- Structural analysis

| Rule | Description | Severity |
|------|-------------|----------|
| PLC-002 | Missing watchdog timer | warning |
| PLC-004 | Array access without bounds check | warning |
| PLC-013 | Variable naming convention (PLCopen) | info |
| PLC-014 | Variable without initial value | info |
| PLC-015 | Function block >200 lines | warning |
| PLC-016 | I/O variable missing comment | info |
| PLC-023 | Nesting depth >4 levels | warning |
| PLC-024 | Unused variable | info |

### Level 3 -- Semantic analysis

| Rule | Description | Severity |
|------|-------------|----------|
| PLC-007 | Output without interlock | warning |
| PLC-008 | Race condition (multiple writes) | error |
| PLC-009 | Missing emergency stop handling | error |
| PLC-017 | Sensor without range validation | warning |
| PLC-018 | Communication without timeout | error |
| PLC-019 | Output without fail-safe default | warning |

---

## Control Flow Graph Analysis

Builds a CFG from ST code for deep semantic analysis:

```python
from src.plc import CFGAnalyzer

source = '''
PROGRAM Main
VAR
    x : INT := 0;
    y : INT;
END_VAR
IF x > 0 THEN
    y := x * 2;
END_IF;
y := 999;  // Dead store: y is immediately overwritten
END_PROGRAM
'''

findings = CFGAnalyzer.analyze(source)
for f in findings:
    print(f"[{f['rule_id']}] {f['severity']}: {f['description']}")
```

| Finding | ID | Description |
|---------|-----|-------------|
| Unreachable code | CFG-001 | Blocks with no incoming edges |
| Loop without exit | CFG-002 | Infinite loop detection |
| Used before defined | CFG-003 | Def-use chain violation |
| Dead store | CFG-004 | Variable defined but never read |
| High cyclomatic complexity | CFG-005 | Complexity >15 |

---

## External Tool Integration

Adapters for external PLC static analysis tools:

| Tool | Detection | Capability |
|------|-----------|------------|
| **IEC Checker** | `iec-checker` in PATH | IEC 61131-3 compliance, type checking, dead code |
| **plc-lint** | `plc-lint` in PATH | Lightweight ST linter |
| **CODESYS CLI** | Common install paths | CODESYS analysis (placeholder) |
| **Custom** | Configurable | Any tool with line-based output |

Tools are auto-detected and run in parallel. Findings are merged with built-in rules.

### Adding a Custom Tool

```python
from src.plc import ExternalAnalyzer, GenericTool

# Create a custom tool adapter
my_tool = GenericTool(
    tool_name="MyPLCChecker",
    command=["my-plc-checker", "--format", "line", "{file}"],
)

# Add to analyzer and run
analyzer = ExternalAnalyzer(extra_tools=[my_tool])
violations = analyzer.analyze("path/to/code.st")
```

---

## Hardware Configuration Verification

Parses and validates TIA Portal hardware configuration XML.

### Parsed Components

- **CPU**: Model, firmware, article number, protection level, watchdog, web server, OPC-UA
- **I/O Modules**: Type, slot, addresses, safety/redundancy flags
- **Network**: Protocol, IP, PROFINET DCP, port security, encryption
- **Safety**: F-CPU, SIL level, safety programs, passwords

### Validation Rules

| Rule | Description | Severity |
|------|-------------|----------|
| HW-001 | Known vulnerable firmware version | critical |
| HW-002 | CPU protection level too low (Level 0) | error |
| HW-003 | Cycle watchdog disabled or too long | warning |
| HW-004 | Safety I/O without redundancy | warning |
| HW-005 | Safety CPU without safety program | error |
| HW-006 | PROFINET without port security | warning |
| HW-007 | Safety CPU without password | critical |
| HW-008 | Web server on unencrypted port (HTTP) | warning |
| HW-009 | Unencrypted communication (S7comm) | warning |
| HW-010 | Safety watchdog mismatch | warning |
| HW-011 | Low CPU memory | info |
| HW-012 | Article number/model mismatch | info |

### Usage

```python
from src.plc.hw_config import HWConfigParser, HWConfigRulesChecker

# Parse hardware configuration
config = HWConfigParser.parse_file("HWConfig.xml")

print(f"CPU Model: {config.cpu.model}")
print(f"Firmware: {config.cpu.firmware_version}")
print(f"Protection Level: {config.cpu.protection_level}")
print(f"Watchdog: {config.cpu.cycle_watchdog_ms}ms")
print(f"Web Server: {config.cpu.web_server_enabled}")
print(f"Safety CPU: {config.cpu.is_safety_cpu}")
print(f"I/O Modules: {len(config.io_modules)}")
print(f"Network Interfaces: {len(config.networks)}")

# Run validation rules
violations = HWConfigRulesChecker.check(config)
for v in violations:
    print(f"[{v.rule_id}] {v.severity}: {v.description}")
    print(f"  Suggestion: {v.suggestion}")
```

---

## LLM Fine-tuning Data Pipeline

Generates training datasets for fine-tuning a PLC-specialized LLM.

### Data Sources

| Source | Description | Examples |
|--------|-------------|----------|
| Rule-based | Each rule -> violation/fixed code pairs | ~30 |
| Vulnerability DB | 20+ CWE-mapped PLC vulnerability patterns | ~40 |
| Few-shot | Curated (bad_code, review, fix) triples | 3+ |
| Codebase scan | Real code -> rule findings -> training pairs | Unlimited |

### Export Formats

- **JSONL** (OpenAI/Anthropic fine-tuning format)
- **Alpaca** (instruction/input/output JSON)
- **ShareGPT** (conversation JSON)

### Usage

```bash
# Generate from rules + vulnerability DB
python -m src.plc.finetune.cli --output ./data/training.jsonl

# Generate from a real codebase
python -m src.plc.finetune.cli --repo /path/to/plc/project --output ./data/training.jsonl

# Export in Alpaca format with train/val/test split
python -m src.plc.finetune.cli --format alpaca --split --output-dir ./data/

# Print statistics
python -m src.plc.finetune.cli --stats
```

### Programmatic API

```python
from src.plc.finetune import DatasetGenerator, PLCPromptBuilder, DomainContext

# Generate dataset
gen = DatasetGenerator()
examples = gen.generate_all(repo_path="/path/to/plc/project")
train, val, test = gen.split_dataset(examples)
gen.export_jsonl(train, "train.jsonl")

# Build specialized prompts
builder = PLCPromptBuilder()
prompt = builder.build_safety_review_prompt(code, safety_level="SIL2")
prompt = builder.build_chain_of_thought_prompt(code)
prompt = builder.build_vulnerability_prompt(code, "buffer overflow")

# Access domain knowledge
patterns = DomainContext.get_vulnerability_patterns()
guidelines = DomainContext.get_review_guidelines()
quirks = DomainContext.get_vendor_quirks()
```

### Vulnerability Pattern Library (20+ CWEs)

| CWE | Vulnerability | Severity |
|-----|---------------|----------|
| CWE-482 | Comparing instead of assigning (`=` vs `:=`) | error |
| CWE-119 | Array out-of-bounds access | critical |
| CWE-670 | Output race condition | error |
| CWE-250 | Unnecessary elevated privileges | critical |
| CWE-362 | Shared variable without synchronization | error |
| CWE-190 | Integer overflow | error |
| CWE-369 | Division by zero | critical |
| CWE-478 | CASE without default branch | warning |
| CWE-798 | Hardcoded credentials | critical |
| CWE-676 | Use of dangerous function (GOTO) | warning |
| CWE-457 | Use of uninitialized variable | error |
| CWE-835 | Infinite loop | critical |
| CWE-628 | Function call with wrong arguments | error |
| CWE-120 | String buffer overflow | error |
| CWE-195 | Signed/unsigned conversion error | warning |
| CWE-665 | Improper initialization | warning |
| CWE-820 | Missing synchronization | error |
| CWE-284 | Improper access control | critical |
| CWE-311 | Sensitive data unencrypted | error |
| CWE-693 | Protection mechanism failure | critical |
| CWE-754 | Insufficient exception checking | warning |

### Domain Knowledge Base

- **20+ vulnerability patterns** with CWE mappings, example code, and fixes
- **12 PLCopen coding guidelines** with good/bad examples
- **15 IEC 61131-3 standard references**
- **4 vendor-specific quirks** (Siemens, Beckhoff, CODESYS, Rockwell)
- **3 curated few-shot examples** for prompt engineering

---

## Project Structure

```
intelligent-code-review-agent/
+-- src/
|   +-- main.py                    # CLI entry point
|   +-- config.py                  # Configuration (pydantic-settings)
|   +-- agent/
|   |   +-- review_agent.py        # Main orchestration (CodeReviewAgent)
|   |   +-- prompts.py             # LLM system prompts and templates
|   +-- parsing/
|   |   +-- context_builder.py     # File reading + context assembly
|   |   +-- ast_extractor.py       # Language-agnostic AST extraction (28 languages)
|   |   +-- diff_parser.py         # Git diff parsing
|   |   +-- language_support.py    # Tree-sitter language loading (23 grammars)
|   +-- plc/                       # Industrial PLC analysis (core)
|   |   +-- simatic_parser.py      # Siemens TIA Portal (SimaticML)
|   |   +-- twincat_parser.py      # Beckhoff TwinCAT 3 (TcPOU)
|   |   +-- codesys_parser.py      # CODESYS V3 (WAGO, Schneider, etc.)
|   |   +-- rockwell_parser.py     # Rockwell/Allen-Bradley (L5X)
|   |   +-- abb_parser.py          # ABB Automation Builder
|   |   +-- ge_parser.py           # GE/Fanuc Proficy Machine Edition
|   |   +-- omron_parser.py        # Omron Sysmac Studio (.smc2)
|   |   +-- xml_parser.py          # Generic PLC XML fallback
|   |   +-- ld_converter.py        # Ladder Diagram -> ST
|   |   +-- fbd_converter.py       # Function Block Diagram -> ST
|   |   +-- sfc_converter.py       # Sequential Function Chart -> ST
|   |   +-- st_extractor.py        # ST variable/function extractor
|   |   +-- plc_rules.py           # 30+ PLC rules (3 levels)
|   |   +-- cfg_analyzer.py        # Control Flow Graph analysis
|   |   +-- external_analyzer.py   # External tool integration
|   |   +-- hw_config.py           # Hardware config parser + verifier
|   |   +-- finetune/              # LLM fine-tuning pipeline
|   |       +-- domain_context.py      # IEC 61131-3 knowledge base
|   |       +-- prompt_builder.py      # PLC-specialized prompts
|   |       +-- dataset_generator.py   # Training data generation
|   |       +-- cli.py                 # Fine-tuning CLI entry point
|   +-- output/
|   |   +-- models.py              # ReviewComment, ReviewReport
|   |   +-- severity.py            # Severity classification
|   |   +-- formatter.py           # Output formatting (JSON/Markdown)
|   +-- rag/
|   |   +-- retriever.py           # ChromaDB guideline retrieval
|   |   +-- loader.py              # Document loading
|   +-- git/
|   |   +-- reader.py              # Git diff extraction
|   |   +-- repo_manager.py        # Git repository management
|   |   +-- models.py              # DiffResult model
+-- api/                           # FastAPI backend
|   +-- main.py                    # App setup, CORS, static files
|   +-- models.py                  # Pydantic request/response models
|   +-- routes/
|       +-- scan.py                # Scan job management endpoints
|       +-- report.py              # Report retrieval endpoints
|       +-- file_scan.py           # Single file upload & scan
|       +-- guidelines.py          # Guideline CRUD + vector indexing
|       +-- config.py              # Config & language list endpoints
+-- web/                           # Vue 3 frontend
|   +-- src/
|   |   +-- App.vue                # Layout with sidebar navigation
|   |   +-- main.ts                # Vue app entry point
|   |   +-- router/index.ts        # Client-side routing
|   |   +-- stores/                # Pinia state management
|   |   |   +-- scan.ts            # Scan job state + API calls
|   |   +-- services/
|   |   |   +-- api.ts             # Axios API client + type definitions
|   |   +-- views/
|   |   |   +-- HomeView.vue       # Dashboard with report list
|   |   |   +-- ScanView.vue       # New scan form + progress tracking
|   |   |   +-- FileScanView.vue   # Drag-and-drop file scan
|   |   |   +-- ReportView.vue     # Full report viewer
|   |   |   +-- CompareView.vue    # Side-by-side report comparison
|   |   |   +-- GuidelinesView.vue # Guideline file management
|   |   |   +-- SettingsView.vue   # Config & language display
|   |   +-- components/
|   |   |   +-- LanguageSwitcher.vue  # UI language selector
|   |   +-- locales/               # i18n translations
|   |       +-- en.ts              # English
|   |       +-- zh.ts              # Chinese
|   |       +-- de.ts              # German
|   |       +-- cs.ts              # Czech
|   +-- package.json
|   +-- vite.config.ts
|   +-- tsconfig.json
+-- tests/                         # Test suite (107 tests)
|   +-- test_diff_parser.py        # Diff parsing tests
|   +-- test_output_models.py      # Output model tests
|   +-- test_review_agent.py       # Review agent tests
|   +-- test_ast_extractor.py      # AST extraction tests
|   +-- test_rag.py                # RAG tests
|   +-- test_fbd_converter.py      # FBD conversion tests
|   +-- test_hw_config.py          # Hardware config tests
|   +-- test_finetune.py           # Fine-tuning pipeline tests
+-- data/
|   +-- guidelines/                # RAG knowledge base (Markdown)
|   |   +-- clean_code_principles.md
|   |   +-- python_best_practices.md
|   |   +-- security_checklist.md
|   +-- plc/
|   |   +-- plcopen_guidelines.md  # PLCopen coding guidelines
|   |   +-- secure_plc_practices.md # PLC security practices
|   +-- vectorstore/               # ChromaDB vector database
+-- docs/
+-- pyproject.toml                 # Project configuration
+-- README.md                      # English documentation
+-- README_CN.md                   # Chinese documentation
+-- .env                           # API keys + configuration
```

---

## Configuration Reference

All settings via environment variables or `.env` file:

| Setting | Default | Description |
|---------|---------|-------------|
| `ANTHROPIC_API_KEY` | -- | Anthropic API key |
| `ANTHROPIC_BASE_URL` | -- | Custom endpoint (e.g., Mimo) |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model ID (see [Model Configuration](#model-configuration)) |
| `DISABLE_THINKING` | `false` | Disable thinking for reasoning models (required for Mimo) |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer for RAG |
| `VECTORSTORE_DIR` | `./data/vectorstore` | ChromaDB path |
| `CONFIDENCE_THRESHOLD` | `0.6` | Min confidence for findings |
| `MAX_CONTEXT_TOKENS` | `8000` | Token budget for context |
| `TEMPERATURE` | `0.0` | LLM temperature |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CUSTOM_GUIDELINES_DIR` | `./data/custom_guidelines` | Custom guideline upload directory |
| `MAX_UPLOAD_SIZE_MB` | `10` | Max guideline file upload size |

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/test_hw_config.py -v
python -m pytest tests/test_fbd_converter.py -v
python -m pytest tests/test_finetune.py -v
```

---

## Market Coverage

| Region | Vendors Covered | Approx. Market Share |
|--------|----------------|---------------------|
| **Europe** | Siemens, Beckhoff, CODESYS (WAGO, Schneider, ABB AC500, Bosch Rexroth, Phoenix Contact) | ~96% |
| **Americas** | Rockwell/Allen-Bradley, GE/Fanuc, Siemens | ~96% |
| **Asia-Pacific** | Omron, Mitsubishi (not supported), Siemens | ~85% |

---

## FAQ

### How do I review only PLC files without Python/JS/other languages?

The tool automatically detects file extensions. `.st`, `.iecst`, and PLC-related `.xml` files are recognized as PLC code and receive deep analysis. Other languages (Python, JS, etc.) only get LLM review.

### My CODESYS project is a ZIP archive. Can I review it directly?

Not yet. Extract the ZIP first, then point to the directory containing the XML files. Omron `.smc2` format (also a ZIP) is supported for automatic extraction.

### How do I add custom review rules?

Add a new rule to the `PATTERN_RULES` list in `src/plc/plc_rules.py`:

```python
PATTERN_RULES.append({
    "id": "PLC-CUSTOM-001",
    "name": "My custom rule",
    "pattern": r"your_regex_here",
    "severity": "warning",
    "description": "Description of the issue",
    "suggestion": "How to fix it",
})
```

### What model should I fine-tune with the generated data?

- **JSONL format**: OpenAI GPT series, Anthropic Claude
- **Alpaca format**: LLaMA, Qwen, and other open-source models
- **ShareGPT format**: Vicuna, ChatGLM, and other conversation models

### Which PLC brands does hardware config verification support?

Currently only **Siemens TIA Portal** HWConfig XML. Support for Rockwell, CODESYS, and Omron hardware configs is planned for future releases.

### How do I use a custom API endpoint (e.g., Mimo)?

Set these in your `.env` file:

```env
ANTHROPIC_BASE_URL=https://your-endpoint.com/v1
ANTHROPIC_API_KEY=your-key
DISABLE_THINKING=true
```

---

## License

MIT
