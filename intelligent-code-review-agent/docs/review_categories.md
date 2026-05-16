# Review Categories

## Categories

| Category | Description | Example Issues |
|----------|-------------|----------------|
| code_style | Naming, formatting, idioms | `variable_name` vs `variableName` in Python |
| potential_bug | Logic errors, edge cases | Missing null check, off-by-one error |
| security | Input validation, secrets, injection | SQL injection, hardcoded API key |
| architecture | Design patterns, SOLID, coupling | God class, circular dependency |
| readability | Complexity, comments, naming clarity | Function too long, unclear variable names |
| convention | Project-specific rules | Missing docstring per project policy |
| performance | Inefficiency, resource waste | N+1 query, unnecessary loop |

## Severity Levels

| Level | Description | Action Required |
|-------|-------------|-----------------|
| info | Suggestion, nice-to-have | Optional improvement |
| warning | Should fix, not blocking | Recommended fix before merge |
| error | Must fix before merge | Blocking issue |
| critical | Security/architecture issue | Blocks merge, requires immediate attention |

## Confidence Threshold

The agent assigns a confidence score (0.0–1.0) to each finding:
- **≥ 0.8**: High confidence — report as-is
- **0.6–0.8**: Medium confidence — report but note uncertainty
- **< 0.6**: Low confidence — filter out to reduce false positives

## Category-Specific Guidelines

### Security
- SQL injection (critical)
- XSS vulnerabilities (critical)
- Hardcoded secrets (critical)
- Missing input validation (error)
- Insecure crypto (error)

### Potential Bug
- Null/None pointer risks (warning–error)
- Off-by-one errors (warning)
- Missing error handling (warning)
- Race conditions (warning–error)
- Resource leaks (warning)

### Code Style
- Naming convention violations (info)
- Import ordering (info)
- Whitespace issues (info)

### Architecture
- Circular dependencies (error)
- God classes/functions (warning)
- Tight coupling (warning)

### Performance
- N+1 queries (warning)
- Unnecessary allocations (info)
- Missing caching (info)

### Readability
- Functions > 50 lines (info)
- Unclear naming (info)
- Missing comments for complex logic (info)

### Convention
- Missing docstrings (info)
- Wrong docstring format (info)
- Missing type hints (info)
