"""PLC-specialized prompt engineering for code review.

Provides domain-aware system prompts, few-shot examples, chain-of-thought
prompting, and targeted vulnerability search prompts for IEC 61131-3 code.
"""

from .domain_context import DomainContext


class PLCPromptBuilder:
    """Build specialized prompts for PLC code review."""

    def __init__(self):
        self.domain = DomainContext()

    def build_system_prompt(self, specialization: str = "general") -> str:
        """Build a domain-aware system prompt for PLC code review.

        Args:
            specialization: One of "general", "safety", "security", "performance"
        """
        base = """You are an expert industrial automation code reviewer specializing in IEC 61131-3 Structured Text (ST) and PLC programming.

## Your Expertise
- Deep knowledge of IEC 61131-3 standard (all 5 languages: ST, LD, FBD, SFC, IL)
- Industrial safety standards: IEC 61508 (SIL), IEC 62061 (SIL), ISO 13849 (PL)
- Industrial cybersecurity: IEC 62443, NIST 800-82
- Vendor-specific quirks: Siemens (TIA Portal/SCL), Beckhoff (TwinCAT), CODESYS, Rockwell (Studio 5000), ABB, GE, Omron

## Key Differences from General Code Review
1. **Execution model**: PLC code runs cyclically (OB1 main cycle). Every scan cycle executes ALL code. Timing matters.
2. **No dynamic memory**: All variables are statically allocated. No heap, no garbage collection.
3. **Deterministic execution**: Code must complete within cycle time. Non-terminating loops crash the PLC.
4. **Safety-critical**: Bugs can cause physical harm. Wrong outputs = damaged equipment or injured people.
5. **Real-time constraints**: Code must complete within watchdog timeout (typically 150ms).
6. **Hardware-bound**: Variables map to physical I/O. Wrong logic = wrong physical action.
7. **No exception handling**: Division by zero, array out-of-bounds = PLC fault (stops).

## Common PLC Vulnerability Patterns
- Array access without bounds check → PLC fault (CWE-119)
- Division by zero → PLC fault (CWE-369)
- Race condition: multiple writes to same output (CWE-670)
- Missing CASE default → undefined output state (CWE-478)
- Infinite loop → watchdog timeout (CWE-835)
- Hardcoded credentials (CWE-798)
- Uninitialized variables (CWE-457)
- Integer overflow in arithmetic (CWE-190)
- Missing safety interlock (CWE-250)
"""

        if specialization == "safety":
            base += """
## Safety Review Focus
- Check for emergency stop handling on all physical outputs
- Verify safety interlocks are in place
- Ensure fail-safe defaults (outputs go to safe state on error)
- Check watchdog timer configuration
- Verify SIL/PL level requirements are met
- Look for single-point-of-failure in safety logic
- Ensure safety functions are not bypassable
"""
        elif specialization == "security":
            base += """
## Security Review Focus
- Check for hardcoded credentials or keys
- Verify access control on critical functions
- Look for unprotected communication channels
- Check for buffer overflows in string/array operations
- Verify input validation on external data
- Look for information disclosure in diagnostics
- Check for denial-of-service via resource exhaustion
"""
        elif specialization == "performance":
            base += """
## Performance Review Focus
- Identify code that may exceed cycle time
- Look for unnecessary computations in main cycle
- Check for inefficient data structures
- Verify proper use of tasks and priorities
- Look for redundant calculations
- Check string operation efficiency
"""

        return base

    def build_few_shot_prompt(self, code: str, examples: list | None = None) -> str:
        """Build a prompt with few-shot examples for PLC code review."""
        if examples is None:
            examples = self.domain.get_few_shot_examples()

        prompt_parts = [self.build_system_prompt()]
        prompt_parts.append("\n## Examples\n")

        for i, ex in enumerate(examples[:3], 1):
            prompt_parts.append(f"### Example {i}")
            prompt_parts.append(f"**Task**: {ex.instruction}\n")
            prompt_parts.append(f"**Code**:\n```st\n{ex.bad_code}\n```\n")
            prompt_parts.append(f"**Review**:\n```json\n{ex.review_comment}\n```\n")
            prompt_parts.append(f"**Fixed**:\n```st\n{ex.fixed_code}\n```\n---\n")

        prompt_parts.append(f"\n## Now Review This Code\n```st\n{code}\n```")
        prompt_parts.append("\nProvide your review as a JSON array of findings.")

        return "\n".join(prompt_parts)

    def build_chain_of_thought_prompt(self, code: str) -> str:
        """Build a chain-of-thought prompt for complex PLC logic analysis."""
        return f"""{self.build_system_prompt()}

## Analysis Instructions

Analyze the following Structured Text code step by step:

1. **Execution Flow**: Trace the execution path. What happens each scan cycle?
2. **Data Flow**: How do variables flow through the logic? Are there uninitialized reads?
3. **Safety Analysis**: Are all safety interlocks present? What happens on sensor failure?
4. **Edge Cases**: What happens with boundary values? Max/min inputs? Simultaneous events?
5. **Timing**: Could this code exceed cycle time? Are there blocking operations?
6. **Concurrency**: If this runs in a task, are shared variables properly protected?
7. **Failure Modes**: What happens if a sensor fails? Communication drops? Power fluctuates?

## Code to Analyze
```st
{code}
```

## Your Analysis

Walk through each step above, then provide your findings as a JSON array:
```json
[
  {{
    "file_path": "...",
    "line_start": N,
    "line_end": N,
    "severity": "critical|error|warning|info",
    "category": "SAFETY|PLC_SECURITY|POTENTIAL_BUG|CONVENTION",
    "title": "...",
    "description": "...",
    "suggestion": "...",
    "confidence": 0.0-1.0
  }}
]
```"""

    def build_vulnerability_prompt(self, code: str, vulnerability_type: str) -> str:
        """Build a targeted vulnerability search prompt."""
        patterns = self.domain.get_vulnerability_patterns()
        matching = [p for p in patterns if vulnerability_type.lower() in p.name.lower()
                    or vulnerability_type.lower() in p.cwe_id.lower()]

        if not matching:
            matching = patterns[:3]

        vuln_desc = "\n".join(
            f"- **{p.name}** ({p.cwe_id}): {p.description}"
            for p in matching
        )

        return f"""{self.build_system_prompt()}

## Targeted Vulnerability Search

Search specifically for these vulnerability patterns:
{vuln_desc}

## Example of vulnerable code:
```st
{matching[0].example_vulnerable}
```

## Example of fixed code:
```st
{matching[0].example_fixed}
```

## Code to Review
```st
{code}
```

Look carefully for these specific vulnerability patterns. Report all matches as a JSON array.
If no matches found, return an empty array []."""

    def build_safety_review_prompt(self, code: str, safety_level: str = "SIL2") -> str:
        """Build a safety integrity level aware review prompt."""
        level_desc = {
            "SIL1": "Safety Integrity Level 1 — Low demand mode, PFD 0.1-0.01",
            "SIL2": "Safety Integrity Level 2 — Low/high demand mode, PFD 0.01-0.001",
            "SIL3": "Safety Integrity Level 3 — High demand mode, PFD 0.001-0.0001",
            "SIL4": "Safety Integrity Level 4 — Continuous mode, PFD 0.0001-0.00001",
            "PLd": "Performance Level d (ISO 13849)",
            "PLe": "Performance Level e (ISO 13849) — highest",
        }
        level_info = level_desc.get(safety_level, safety_level)

        return f"""{self.build_system_prompt(specialization="safety")}

## Safety Review: {safety_level}

**Target safety level**: {level_info}

### Safety Requirements for {safety_level}
- Redundant sensor inputs for critical measurements
- Diagnostic coverage >99% for SIL3, >90% for SIL2
- Common cause failure prevention (diverse implementation)
- Fail-safe outputs (de-energize to safe state)
- Watchdog monitoring with safe-state transition
- Emergency stop handling with manual reset required
- Cross-monitoring between redundant channels

## Code to Review
```st
{code}
```

Evaluate this code against {safety_level} requirements. Report:
1. Missing safety functions
2. Insufficient diagnostic coverage
3. Single points of failure
4. Bypass risks
5. Common cause failure vulnerabilities

Provide findings as a JSON array."""

    def get_all_prompts(self) -> dict[str, str]:
        """Return all prompt templates for fine-tuning dataset generation."""
        return {
            "system": self.build_system_prompt(),
            "system_safety": self.build_system_prompt("safety"),
            "system_security": self.build_system_prompt("security"),
            "system_performance": self.build_system_prompt("performance"),
        }
