# Architecture Documentation

## Overview

The Intelligent Code Review Agent is a single-agent system that uses Claude (Anthropic) to analyze code changes and provide structured review feedback. The system follows a layered architecture with a web frontend, REST API backend, and core analysis engine.

```
┌─────────────────────────────────────────────────────────────────┐
│  Web Frontend (Vue 3 + TypeScript)                              │
│  Dashboard · Scan · File Scan · Report · Compare · Guidelines  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / REST
┌──────────────────────────▼──────────────────────────────────────┐
│  API Layer (FastAPI)                                            │
│  /api/scan/* · /api/report/* · /api/file-scan · /api/guidelines │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  Core Engine                                                    │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────────┐ │
│  │   Git   │→ │  Parser  │→ │   RAG   │→ │   LLM (Claude)   │ │
│  │  Diff   │  │ Context  │  │Retriever│  │                  │ │
│  │ Reader  │  │ Builder  │  │(ChromaDB│  │                  │ │
│  └─────────┘  └──────────┘  └─────────┘  └──────────────────┘ │
│                     │                           │               │
│  ┌──────────────────▼───────────────────────────▼─────────────┐ │
│  │              PLC Analysis Pipeline                         │ │
│  │  Vendor Parsers (7) → Converters (LD/FBD/SFC) → Analysis  │ │
│  │  Rules (30+) · CFG · External Tools · HW Config           │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Web Layer (`web/`)

Vue 3 SPA with TypeScript, Pinia state management, and vue-i18n (4 languages).

- **Views**: HomeView (dashboard), ScanView (new scan), FileScanView (drag-and-drop), ReportView, CompareView, GuidelinesView, SettingsView
- **Router**: Client-side routing with lazy-loaded components
- **API Client**: Axios-based HTTP client with typed interfaces
- **i18n**: English, Chinese, German, Czech translations

### 2. API Layer (`api/`)

FastAPI backend providing REST endpoints and serving the built frontend.

- **Routes**: Modular routers for scan, report, file-scan, guidelines, config
- **Models**: Pydantic request/response models for type-safe API contracts
- **Background Jobs**: Threading-based scan job execution with progress polling
- **Static Files**: Serves built Vue SPA in production

### 3. Git Layer (`src/git/`)

Responsible for repository access and diff extraction.

- **RepoManager**: Wraps GitPython to clone repos, get diffs, read file content
- **DiffParser**: Parses unified diff text into structured `DiffHunk` models
- **Models**: Pydantic models for `DiffResult`, `ChangedFile`, `DiffHunk`, `DiffLine`

### 4. Parsing Layer (`src/parsing/`)

Extracts code context around changes using Tree-sitter AST parsing (23 language grammars).

- **LanguageSupport**: Manages Tree-sitter grammar loading per language
- **ASTExtractor**: Given changed line ranges, finds enclosing functions/classes/imports
- **ContextBuilder**: Combines diff + AST to build review context for the LLM

### 5. Agent Layer (`src/agent/`)

The core review logic using LangChain and Claude.

- **CodeReviewAgent**: Main orchestrator — takes diff, builds context, calls Claude, parses output
- **Prompts**: System prompt and review template with structured JSON output format
- **Chains**: Specialized review chains for style, security, bugs, performance
- **Tools**: LangChain tools for file access, diff parsing, guideline search

### 6. RAG Layer (`src/rag/`)

Retrieval-Augmented Generation for project-specific guidelines.

- **DocumentLoader**: Loads markdown docs, code files, and project guidelines
- **GuidelineIndexer**: Indexes documents into ChromaDB vector store
- **GuidelineRetriever**: Retrieves relevant guidelines during review

### 7. Output Layer (`src/output/`)

Formats review results into various output formats.

- **Models**: `ReviewComment` and `ReviewReport` with severity/category enums
- **Formatter**: JSON, Markdown, and inline comment formatters
- **SeverityClassifier**: Validates and classifies issue severity

## Data Flow

1. **Input**: Git repo path + commit SHA, branch diff, or single file upload
2. **Diff Extraction**: RepoManager gets the diff, DiffParser structures it (or file content is read directly)
3. **Context Building**: For each changed file/hunk, ASTExtractor finds enclosing scope (23 languages)
4. **RAG Enhancement**: Relevant guidelines retrieved and injected into prompt
5. **LLM Review**: Claude analyzes each change with full context
6. **Output**: Structured ReviewReport with severity-graded comments, stored and served via API

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangChain | Mature ecosystem, good Claude integration |
| AST parsing | Tree-sitter | Fast, multi-language, incremental (23 grammars) |
| Vector store | ChromaDB | Easy setup, persistent, good for prototyping |
| Output format | Pydantic JSON | Type-safe, validatable, extensible |
| Architecture | Single agent | Simpler for MVP, sufficient for 4-sprint timeline |
| Temperature | 0.0 | Deterministic, reproducible results |
| Web framework | FastAPI + Vue 3 | Async Python, modern TypeScript SPA |
| i18n | vue-i18n | 4 languages (en, zh, de, cs) |
