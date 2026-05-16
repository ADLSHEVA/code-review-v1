# Intelligent Code Review Agent — Detailed Project Plan
## For Coding Agent Implementation Guidance

---

## 1. Project Overview

**Goal**: Build an AI-powered code review agent that analyzes git diffs / Pull Requests and produces structured, context-aware review feedback.

**Core Tech Stack**:
- Python 3.11+
- LangChain (agent framework)
- Claude API (Anthropic) as LLM
- Tree-sitter (AST parsing)
- GitPython (repository access)
- ChromaDB or FAISS (vector store for RAG)
- Pydantic (structured output validation)

**Architecture**: Single-agent with tool use (MVP). Future: multi-agent via LangGraph.

---

## 2. Project Structure

```
intelligent-code-review-agent/
├── README.md
├── pyproject.toml                 # Project config (use Poetry or pip)
├── .env.example                   # ANTHROPIC_API_KEY, etc.
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Settings, env vars, constants
│   │
│   ├── git/                       # Git integration layer
│   │   ├── __init__.py
│   │   ├── diff_parser.py         # Parse git diffs into structured format
│   │   ├── repo_manager.py        # Clone, checkout, manage repos via GitPython
│   │   └── models.py              # Data models: DiffHunk, ChangedFile, etc.
│   │
│   ├── parsing/                   # Code parsing layer
│   │   ├── __init__.py
│   │   ├── ast_extractor.py       # Tree-sitter AST context extraction
│   │   ├── context_builder.py     # Build review context from AST + diff
│   │   └── language_support.py    # Tree-sitter grammar loading per language
│   │
│   ├── agent/                     # LangChain agent
│   │   ├── __init__.py
│   │   ├── review_agent.py        # Main agent orchestration
│   │   ├── prompts.py             # System prompts, review templates
│   │   ├── tools.py               # LangChain tools (git, ast, rag)
│   │   └── chains.py              # Review chains (style, security, architecture)
│   │
│   ├── rag/                       # RAG layer
│   │   ├── __init__.py
│   │   ├── indexer.py             # Index project docs into vector store
│   │   ├── retriever.py           # Retrieve relevant guidelines
│   │   └── document_loader.py     # Load markdown, txt, code files
│   │
│   ├── output/                    # Output formatting
│   │   ├── __init__.py
│   │   ├── models.py              # Pydantic models: ReviewComment, ReviewReport
│   │   ├── formatter.py           # Format output as JSON, Markdown, etc.
│   │   └── severity.py            # Severity classification logic
│   │
│   └── plc/                       # PLC extension (Stretch Goal)
│       ├── __init__.py
│       ├── xml_parser.py          # SimaticML / TcPOU XML parsing
│       ├── st_extractor.py        # Extract Structured Text from XML
│       └── plc_rules.py           # PLCopen + Secure PLC Coding rules
│
├── tests/
│   ├── __init__.py
│   ├── test_diff_parser.py
│   ├── test_ast_extractor.py
│   ├── test_review_agent.py
│   ├── test_rag.py
│   ├── test_output_models.py
│   └── fixtures/                  # Sample diffs, code files, repos
│       ├── sample_diff.patch
│       ├── sample_python_file.py
│       └── sample_guidelines.md
│
├── docs/
│   ├── architecture.md            # Architecture documentation
│   ├── review_categories.md       # Review category definitions
│   └── plc_extension.md           # PLC extension design doc
│
└── data/
    ├── guidelines/                # Default coding guidelines for RAG
    │   ├── python_best_practices.md
    │   ├── security_checklist.md
    │   └── clean_code_principles.md
    └── plc/                       # PLC-specific (Stretch)
        ├── plcopen_guidelines.md
        └── secure_plc_practices.md
```

---

## 3. Data Models (Define First)

### 3.1 Git Layer Models (`src/git/models.py`)

```python
from pydantic import BaseModel
from enum import Enum

class ChangeType(str, Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    RENAMED = "renamed"

class DiffLine(BaseModel):
    line_number_old: int | None
    line_number_new: int | None
    content: str
    is_added: bool
    is_deleted: bool

class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]

class ChangedFile(BaseModel):
    file_path: str
    change_type: ChangeType
    language: str | None = None        # Detected from extension
    hunks: list[DiffHunk]
    old_content: str | None = None     # Full file before change
    new_content: str | None = None     # Full file after change

class DiffResult(BaseModel):
    """Complete parsed diff for one commit or PR."""
    commit_sha: str | None = None
    base_ref: str | None = None
    head_ref: str | None = None
    files: list[ChangedFile]
```

### 3.2 AST Context Models (`src/parsing/ast_extractor.py`)

```python
from pydantic import BaseModel

class CodeContext(BaseModel):
    """Context extracted via Tree-sitter for a changed region."""
    file_path: str
    language: str
    changed_lines: tuple[int, int]           # (start, end) of change
    enclosing_function: str | None = None    # Full function source
    enclosing_class: str | None = None       # Full class source
    function_name: str | None = None
    class_name: str | None = None
    imports: list[str] = []                  # Import statements in file
    related_symbols: list[str] = []          # Variables/functions referenced
```

### 3.3 Review Output Models (`src/output/models.py`)

```python
from pydantic import BaseModel
from enum import Enum

class Severity(str, Enum):
    INFO = "info"               # Suggestion, nice-to-have
    WARNING = "warning"         # Should fix, not blocking
    ERROR = "error"             # Must fix before merge
    CRITICAL = "critical"       # Security/architecture issue, blocks merge

class ReviewCategory(str, Enum):
    CODE_STYLE = "code_style"
    POTENTIAL_BUG = "potential_bug"
    SECURITY = "security"
    ARCHITECTURE = "architecture"
    READABILITY = "readability"
    CONVENTION = "convention"       # Project-specific conventions
    PERFORMANCE = "performance"

class ReviewComment(BaseModel):
    file_path: str
    line_start: int
    line_end: int | None = None
    severity: Severity
    category: ReviewCategory
    title: str                          # Short summary, e.g. "Missing input validation"
    description: str                    # Detailed explanation
    suggestion: str | None = None       # Suggested fix (code or text)
    confidence: float = 0.8            # Agent's confidence in this finding

class ReviewReport(BaseModel):
    """Complete review for a diff/PR."""
    summary: str                        # High-level summary
    comments: list[ReviewComment]
    stats: dict = {}                    # e.g. {"critical": 1, "error": 3, ...}
    reviewed_files: list[str]
    skipped_files: list[str] = []       # Files too large or binary
```

---

## 4. Sprint 1: Research & Setup

### 4.1 Objectives
- Set up project scaffolding and dev environment
- Evaluate and integrate Tree-sitter for AST parsing
- Integrate GitPython for repository access and diff extraction
- Define review categories and severity levels
- Create basic LangChain agent scaffold

### 4.2 Tasks

#### Task 1.1: Project Setup
```bash
# Initialize project
mkdir intelligent-code-review-agent && cd $_
python -m venv .venv && source .venv/bin/activate

# Core dependencies
pip install langchain langchain-anthropic langchain-community
pip install gitpython
pip install tree-sitter tree-sitter-python tree-sitter-javascript
pip install chromadb
pip install pydantic pydantic-settings
pip install python-dotenv
pip install pytest pytest-asyncio

# Create project structure as defined in Section 2
```

#### Task 1.2: GitPython Integration (`src/git/repo_manager.py`)
Implement:
- `clone_repo(url, target_dir)` — Clone a remote repo
- `get_diff(repo_path, base_ref, head_ref) -> DiffResult` — Get diff between two refs
- `get_diff_from_commit(repo_path, commit_sha) -> DiffResult` — Get diff for a single commit
- `get_file_content(repo_path, file_path, ref) -> str` — Get file content at a specific ref
- `list_changed_files(repo_path, base_ref, head_ref) -> list[str]`

Key implementation notes:
- Use `git.Repo` from GitPython
- Parse unified diff format into `DiffResult` model
- Detect language from file extension (`.py` → Python, `.js` → JavaScript, etc.)
- Handle binary files gracefully (skip them)

#### Task 1.3: Diff Parser (`src/git/diff_parser.py`)
Implement:
- `parse_unified_diff(diff_text: str) -> list[DiffHunk]`
- `extract_changed_line_ranges(hunks: list[DiffHunk]) -> list[tuple[int, int]]`
- Parse `@@` hunk headers to extract line numbers
- Classify lines as added/deleted/context

#### Task 1.4: Tree-sitter Setup (`src/parsing/language_support.py`)
Implement:
- `load_language(lang: str) -> tree_sitter.Language` — Load Tree-sitter grammar
- `parse_file(source_code: str, language: str) -> tree_sitter.Tree`
- Support at minimum: Python, JavaScript/TypeScript
- Graceful fallback for unsupported languages (skip AST, use raw diff only)

#### Task 1.5: AST Context Extraction (`src/parsing/ast_extractor.py`)
Implement:
- `extract_context(source_code, language, changed_lines) -> CodeContext`
- Given changed line ranges, find the enclosing function/method/class
- Extract the full function body + signature
- Extract class-level attributes if change is inside a method
- Extract import statements

Tree-sitter query strategy:
```python
# Pseudocode for finding enclosing function
def find_enclosing_node(tree, line_number, node_types=["function_definition", "class_definition"]):
    """Walk up the tree from the changed line to find the enclosing scope."""
    root = tree.root_node
    target_node = find_node_at_line(root, line_number)
    current = target_node
    while current is not None:
        if current.type in node_types:
            return current
        current = current.parent
    return None
```

#### Task 1.6: Basic LangChain Agent (`src/agent/review_agent.py`)
Implement minimal agent that:
- Takes a code snippet as input
- Sends it to Claude with a basic review prompt
- Returns raw text feedback
- This is just a proof-of-concept — structured output comes in Sprint 2

#### Task 1.7: Define Review Categories
Create `docs/review_categories.md` documenting:

| Category | What it checks | Example |
|----------|---------------|---------|
| code_style | Naming, formatting, idioms | `variable_name` vs `variableName` in Python |
| potential_bug | Logic errors, edge cases | Missing null check, off-by-one |
| security | Input validation, secrets, injection | SQL injection, hardcoded API key |
| architecture | Design patterns, SOLID, coupling | God class, circular dependency |
| readability | Complexity, comments, naming clarity | Function too long, unclear variable names |
| convention | Project-specific rules | Missing docstring per project policy |
| performance | Inefficiency, resource waste | N+1 query, unnecessary loop |

### 4.3 Sprint 1 Deliverable
- Working project scaffold with all directories
- `DiffResult` can be generated from any local git repo
- Tree-sitter can parse Python/JS files and extract enclosing functions for changed lines
- Basic agent can send code to Claude and get text feedback
- All data models defined and tested
- Tests for diff_parser, ast_extractor, repo_manager

---

## 5. Sprint 2: Diff Analysis & Basic Review Agent

### 5.1 Objectives
- Complete the diff → AST → context pipeline
- Build the core review agent with structured output
- Implement review prompt engineering
- Produce structured `ReviewReport` as JSON

### 5.2 Tasks

#### Task 2.1: Context Builder (`src/parsing/context_builder.py`)
Implement the pipeline that combines diff + AST:
```python
def build_review_context(diff_result: DiffResult, repo_path: str) -> list[CodeContext]:
    """For each changed file, extract AST context for each changed region."""
    contexts = []
    for changed_file in diff_result.files:
        if changed_file.language is None:
            continue  # Skip unsupported
        source = read_file(repo_path, changed_file.file_path)
        for hunk in changed_file.hunks:
            changed_lines = (hunk.new_start, hunk.new_start + hunk.new_count)
            ctx = extract_context(source, changed_file.language, changed_lines)
            contexts.append(ctx)
    return contexts
```

Key decision: **How much context to send to the LLM?**
- Always: the diff hunk itself (added/removed lines)
- Always: the enclosing function/method (full body)
- If available: the enclosing class (signature + attributes, not full body)
- If available: import statements
- Never: the entire file (too much noise, wastes context window)

#### Task 2.2: Review Prompts (`src/agent/prompts.py`)

System prompt structure:
```python
SYSTEM_PROMPT = """You are an expert code reviewer. You analyze code changes and provide
structured feedback. You focus on finding real issues, not nitpicking.

For each issue you find, provide:
- file_path: the file containing the issue
- line_start: the starting line number
- line_end: the ending line number (if spans multiple lines)
- severity: one of "info", "warning", "error", "critical"
- category: one of "code_style", "potential_bug", "security", "architecture",
  "readability", "convention", "performance"
- title: a short summary (max 10 words)
- description: detailed explanation of why this is an issue
- suggestion: how to fix it (include code if applicable)
- confidence: your confidence 0.0-1.0

Rules:
- Only report genuine issues. Do not flag things that are correct.
- Prioritize security and bug issues over style issues.
- Consider the surrounding context (enclosing function, class) when evaluating.
- If you're not confident about an issue (< 0.5), don't report it.
- Return your findings as a JSON array of review comments.
"""

REVIEW_TEMPLATE = """
## Code Change to Review

**File**: {file_path}
**Language**: {language}

### Diff (changed lines):
```
{diff_content}
```

### Enclosing Function:
```{language}
{enclosing_function}
```

### Enclosing Class (if applicable):
```{language}
{enclosing_class}
```

### Import Statements:
```{language}
{imports}
```

{rag_context}

Please review this code change and return your findings as a JSON array.
"""
```

#### Task 2.3: Review Agent with Structured Output (`src/agent/review_agent.py`)

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
import json

class CodeReviewAgent:
    def __init__(self, model="claude-sonnet-4-20250514"):
        self.llm = ChatAnthropic(model=model, temperature=0)

    def review_diff(self, diff_result: DiffResult, repo_path: str) -> ReviewReport:
        contexts = build_review_context(diff_result, repo_path)
        all_comments = []

        for ctx in contexts:
            prompt = REVIEW_TEMPLATE.format(
                file_path=ctx.file_path,
                language=ctx.language,
                diff_content=self._get_diff_text(ctx),
                enclosing_function=ctx.enclosing_function or "N/A",
                enclosing_class=ctx.enclosing_class or "N/A",
                imports="\n".join(ctx.imports),
                rag_context=""  # Added in Sprint 3
            )
            response = self.llm.invoke([
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])
            comments = self._parse_response(response.content)
            all_comments.extend(comments)

        return ReviewReport(
            summary=self._generate_summary(all_comments),
            comments=all_comments,
            stats=self._compute_stats(all_comments),
            reviewed_files=[f.file_path for f in diff_result.files]
        )

    def _parse_response(self, response_text: str) -> list[ReviewComment]:
        """Parse LLM JSON response into ReviewComment objects."""
        # Extract JSON from response (handle markdown code blocks)
        # Validate against Pydantic model
        # Filter by confidence threshold
        ...

    def _generate_summary(self, comments: list[ReviewComment]) -> str:
        """Generate a human-readable summary of findings."""
        ...

    def _compute_stats(self, comments: list[ReviewComment]) -> dict:
        """Count issues by severity and category."""
        ...
```

#### Task 2.4: Output Formatter (`src/output/formatter.py`)
Implement:
- `format_as_json(report: ReviewReport) -> str`
- `format_as_markdown(report: ReviewReport) -> str`
- `format_as_inline_comments(report: ReviewReport) -> list[dict]` — for future GitHub integration

Markdown output example:
```markdown
# Code Review Report

## Summary
Found 5 issues: 1 critical, 2 errors, 2 warnings.

## Critical Issues

### [CRITICAL] SQL Injection in `user_service.py:42`
**Category**: Security
**Description**: User input is directly interpolated into SQL query...
**Suggestion**: Use parameterized queries...
```

#### Task 2.5: CLI Entry Point (`src/main.py`)
```python
import argparse

def main():
    parser = argparse.ArgumentParser(description="AI Code Review Agent")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--commit", help="Review a specific commit")
    parser.add_argument("--base", help="Base branch/ref for comparison")
    parser.add_argument("--head", help="Head branch/ref for comparison")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()
    # Run review pipeline
    # Output results
```

Usage:
```bash
# Review last commit
python -m src.main /path/to/repo --commit HEAD

# Review branch diff
python -m src.main /path/to/repo --base main --head feature-branch

# Output as JSON
python -m src.main /path/to/repo --commit HEAD --format json --output review.json
```

### 5.3 Sprint 2 Deliverable
- Full pipeline: git diff → AST context → LLM review → structured JSON output
- CLI tool that can review any local git repo's last commit
- Structured ReviewReport with severity classification
- Markdown and JSON output formatters
- Tests with fixture diffs and expected outputs

---

## 6. Sprint 3: RAG & Refinement

### 6.1 Objectives
- Add RAG over project documentation and coding guidelines
- Detect inconsistencies with existing codebase
- End-to-end evaluation on real repositories
- Improve prompt quality based on testing

### 6.2 Tasks

#### Task 3.1: Document Loader (`src/rag/document_loader.py`)
Implement:
- `load_markdown(file_path) -> list[Document]` — Split by headers
- `load_code_file(file_path) -> list[Document]` — Split by function/class
- `load_directory(dir_path, patterns) -> list[Document]` — Recursively load
- Metadata: file_path, section_title, language, doc_type

Supported sources:
- Project README, CONTRIBUTING.md, STYLEGUIDE.md
- Code files (existing codebase as reference)
- Custom guidelines documents

#### Task 3.2: Indexer (`src/rag/indexer.py`)
```python
from langchain_community.vectorstores import Chroma
from langchain_anthropic import AnthropicEmbeddings  # or use a different embedder
from langchain_community.embeddings import HuggingFaceEmbeddings

class GuidelineIndexer:
    def __init__(self, persist_dir="./data/vectorstore"):
        # Use a local embedding model to avoid API costs
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )

    def index_project(self, project_path: str):
        """Index all relevant docs from a project."""
        docs = []
        # Load README, CONTRIBUTING, etc.
        # Load code files for convention reference
        # Load custom guidelines if present
        self.vectorstore.add_documents(docs)

    def search(self, query: str, k: int = 5) -> list[Document]:
        """Retrieve relevant guidelines for a review context."""
        return self.vectorstore.similarity_search(query, k=k)
```

#### Task 3.3: RAG Integration into Agent
Modify `review_agent.py` to:
1. Before each review, query the vector store with the code context
2. Inject relevant guidelines into the prompt via `{rag_context}`
3. Instruct the LLM to check the code against these guidelines

```python
# In review_diff method:
rag_results = self.retriever.search(
    f"coding guidelines for {ctx.language} {ctx.function_name}"
)
rag_context = "\n\n".join([
    f"### Relevant Guideline:\n{doc.page_content}"
    for doc in rag_results
])
# Insert into REVIEW_TEMPLATE
```

#### Task 3.4: Convention Consistency Checker
Add a check that compares the changed code's patterns against the existing codebase:
- Naming conventions (snake_case vs camelCase usage in project)
- Import ordering patterns
- Docstring style (Google vs NumPy vs reST)
- Error handling patterns

Implementation: index a sample of existing code files, retrieve similar functions/patterns when reviewing new code, and include them as "project convention reference" in the prompt.

#### Task 3.5: Default Guidelines Data
Create `data/guidelines/` with curated content:
- `python_best_practices.md`: PEP 8 highlights, common antipatterns
- `security_checklist.md`: OWASP-inspired checklist for code review
- `clean_code_principles.md`: SOLID, DRY, naming conventions

These serve as fallback guidelines when a project doesn't have its own.

#### Task 3.6: End-to-End Evaluation
Test the complete pipeline on real-world repositories:
1. Pick 3-5 open source repos with known PRs
2. Run the agent on those PRs
3. Compare agent output against actual human review comments
4. Measure: precision (are flagged issues real?), recall (did it miss real issues?), usefulness

Create an evaluation script:
```python
# scripts/evaluate.py
def evaluate_on_repo(repo_url, pr_number, human_review_file):
    """Compare agent review against human review."""
    # Clone repo, checkout PR
    # Run agent
    # Load human review
    # Compare and compute metrics
```

#### Task 3.7: Prompt Refinement
Based on evaluation results:
- Reduce false positives by tightening the system prompt
- Improve severity accuracy
- Add few-shot examples of good reviews to the prompt
- Tune confidence thresholds

### 6.3 Sprint 3 Deliverable
- RAG pipeline: index project docs → retrieve relevant guidelines → inject into review
- Default guidelines for Python + security
- Convention consistency checking
- Evaluation results on real repositories with metrics
- Improved prompts based on evaluation feedback

---

## 7. Sprint 4: Final Delivery

### 7.1 Objectives
- Polish all features, fix bugs
- Complete documentation
- Prepare demo
- Final presentation

### 7.2 Tasks

#### Task 4.1: Bug Fixes & Edge Cases
- Handle repos with no Python/JS files gracefully
- Handle very large diffs (>1000 lines) — chunking strategy
- Handle binary files, images, config files (skip)
- Error handling for API failures (retry with backoff)
- Handle rate limiting from Claude API

#### Task 4.2: Documentation
- Update `README.md` with installation, usage, examples
- Document architecture in `docs/architecture.md`
- Add inline code comments
- Write a "How it works" section with pipeline diagram

#### Task 4.3: Demo Preparation
Prepare a live demo showing:
1. Clone a repo with known issues
2. Run the agent on a specific commit
3. Show the structured output (JSON + Markdown)
4. Show how RAG affects the review (with vs without project guidelines)

#### Task 4.4: Final Presentation
- Update pitch slides with results
- Include before/after examples
- Show evaluation metrics
- Demo video as backup

### 7.3 Sprint 4 Deliverable
- Polished, working code review agent
- Complete documentation
- Demo-ready
- Final presentation

---

## 8. Stretch Goals (If Time Permits)

### 8.1 PLC Structured Text Analysis
- Parse `.st` files (plain text IEC 61131-3 Structured Text)
- Add Tree-sitter grammar for ST (if available) or regex-based parsing
- Add PLCopen guidelines to RAG knowledge base
- Add Secure PLC Coding Practices to RAG
- **Do NOT attempt**: SimaticML XML parsing, Ladder Diagram conversion, TwinCAT XML

### 8.2 GitHub/GitLab PR Integration
- Use GitHub API to fetch PR diffs
- Post review comments directly on the PR via API
- Could be implemented as a GitHub Action

### 8.3 Auto-Fix Suggestions
- Generate patch files for suggested fixes
- Use `temperature=0` for deterministic output
- Validate patches can be applied cleanly

---

## 9. Key Technical Decisions & Rationale

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangChain | Mature ecosystem, good Claude integration, tool use support |
| LLM | Claude (Anthropic) | Strong code understanding, structured output, large context window |
| AST parsing | Tree-sitter | Incremental, multi-language, battle-tested (used in VS Code, GitHub) |
| Vector store | ChromaDB | Easy to set up, persistent, good for prototyping |
| Output format | Pydantic JSON | Type-safe, validatable, extensible |
| Architecture | Single agent (MVP) | Simpler to build/debug, sufficient for 4-sprint timeline |
| Temperature | 0 for reviews | Deterministic, reproducible results |

---

## 10. Risk Mitigations in Code

### LLM Hallucination
```python
# In _parse_response:
# 1. Filter by confidence threshold
comments = [c for c in comments if c.confidence >= 0.6]

# 2. Validate line numbers exist in the actual file
comments = [c for c in comments if c.line_start <= file_line_count]

# 3. Validate file paths exist
comments = [c for c in comments if c.file_path in changed_files]
```

### Context Window Management
```python
# In context_builder.py:
MAX_CONTEXT_TOKENS = 8000  # Leave room for system prompt + response

def truncate_context(context: CodeContext) -> CodeContext:
    """If context is too large, prioritize: diff > function > class > imports."""
    token_count = estimate_tokens(context)
    if token_count > MAX_CONTEXT_TOKENS:
        context.enclosing_class = None  # Drop class context first
    if token_count > MAX_CONTEXT_TOKENS:
        context.imports = []  # Drop imports next
    return context
```

### API Error Handling
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def call_llm(self, messages):
    return self.llm.invoke(messages)
```

---

## 11. Testing Strategy

| Test Type | What | Tool |
|-----------|------|------|
| Unit tests | Diff parser, AST extractor, output models | pytest |
| Integration tests | Full pipeline on fixture repos | pytest + temp git repos |
| Evaluation | Agent accuracy on real PRs | Custom eval script |
| Smoke test | CLI runs without error on sample repo | Shell script |

### Sample test fixture setup:
```python
# tests/conftest.py
import tempfile, git

@pytest.fixture
def sample_repo():
    """Create a temporary git repo with a known commit."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = git.Repo.init(tmpdir)
        # Create initial file
        write_file(tmpdir, "app.py", "def hello():\n    print('hello')\n")
        repo.index.add(["app.py"])
        repo.index.commit("initial")
        # Create a change with a known bug
        write_file(tmpdir, "app.py", "def hello(name):\n    print('hello ' + name)\n")
        repo.index.add(["app.py"])
        repo.index.commit("add name parameter")
        yield tmpdir
```
