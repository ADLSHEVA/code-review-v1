"""IEC 61131-3 domain knowledge base for PLC code review.

Provides structured domain knowledge including:
  - Known PLC vulnerability patterns with CWE mappings
  - PLCopen coding guidelines
  - IEC 61131-3 standard references
  - Curated few-shot examples for LLM training
"""

from pydantic import BaseModel


class PLCVulnerabilityPattern(BaseModel):
    """A known PLC/ICS vulnerability pattern."""
    cwe_id: str               # e.g. "CWE-119"
    name: str
    severity: str             # critical, error, warning, info
    description: str
    st_pattern: str           # Regex or code snippet showing the vulnerability
    example_vulnerable: str   # Example vulnerable ST code
    example_fixed: str        # Example fixed ST code
    iec_reference: str = ""   # IEC 61131-3 section reference
    vendor_notes: str = ""    # Vendor-specific notes


class PLCReviewGuideline(BaseModel):
    """A PLCopen or IEC 61131-3 coding guideline."""
    rule_id: str
    title: str
    description: str
    category: str             # safety, security, reliability, style
    severity: str
    example_good: str = ""
    example_bad: str = ""
    iec_reference: str = ""


class FewShotExample(BaseModel):
    """A curated example for few-shot LLM prompting."""
    instruction: str
    bad_code: str
    review_comment: str
    fixed_code: str
    rule_id: str = ""
    category: str = ""


class DomainContext:
    """IEC 61131-3 domain knowledge provider."""

    @staticmethod
    def get_vulnerability_patterns() -> list[PLCVulnerabilityPattern]:
        """Return known PLC vulnerability patterns."""
        return [
            PLCVulnerabilityPattern(
                cwe_id="CWE-482",
                name="Comparing Instead of Assigning",
                severity="error",
                description="Using comparison operator (=) instead of assignment (:=) in ST. "
                            "This is a common mistake since ST uses := for assignment.",
                st_pattern=r"^\s*\w+\s*=\s*[^=]",
                example_vulnerable='''PROGRAM Main
VAR
    MotorSpeed : INT;
END_VAR
MotorSpeed = 100;  // BUG: = is comparison, not assignment''',
                example_fixed='''PROGRAM Main
VAR
    MotorSpeed : INT;
END_VAR
MotorSpeed := 100;  // Correct assignment operator''',
                iec_reference="IEC 61131-3 Part 3, Section 7.3.1",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-119",
                name="Buffer Overflow via Array Access",
                severity="critical",
                description="Array access without bounds checking can cause memory corruption "
                            "or unexpected behavior on PLC runtime.",
                st_pattern=r"\w+\[\w+\]\s*:=|:=\s*\w+\[\w+\]",
                example_vulnerable='''PROGRAM Main
VAR
    Data : ARRAY[0..99] OF INT;
    Index : INT;
END_VAR
Data[Index] := 42;  // No bounds check on Index''',
                example_fixed='''PROGRAM Main
VAR
    Data : ARRAY[0..99] OF INT;
    Index : INT;
END_VAR
IF (Index >= 0) AND (Index <= 99) THEN
    Data[Index] := 42;
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.5.4",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-670",
                name="Always-Incorrect Control Flow Implementation",
                severity="error",
                description="Race condition: multiple writes to same output in one cycle. "
                            "Last write wins, making behavior non-deterministic.",
                st_pattern=r"(\w+)\s*:=.*;\s*\n.*\1\s*:=",
                example_vulnerable='''// Network 1
Motor := Start AND NOT Stop;
// Network 2 (later in same cycle)
Motor := Override;  // Overwrites Network 1''',
                example_fixed='''Motor := Override OR (Start AND NOT Stop);
// Single consolidated assignment''',
                iec_reference="IEC 61131-3 Part 3, Section 6.8",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-250",
                name="Execution with Unnecessary Privileges",
                severity="critical",
                description="PLC program running without proper protection level. "
                            "Online changes or unauthorized access possible.",
                st_pattern=r"PROGRAM\s+\w+\s*$",
                example_vulnerable='''// Program with no access protection
PROGRAM CriticalSafety
VAR
    EmergencyStop : BOOL;
END_VAR
EmergencyStop := Sensor1 AND Sensor2;''',
                example_fixed='''// Protected program block with access control
FUNCTION_BLOCK CriticalSafety
VAR CONSTANT
    ACCESS_LEVEL : INT := 3;  // Highest protection
END_VAR
VAR
    EmergencyStop : BOOL;
END_VAR
EmergencyStop := Sensor1 AND Sensor2;''',
                iec_reference="IEC 62443-3-3",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-362",
                name="Race Condition in Output Assignment",
                severity="error",
                description="Multiple programs or tasks writing to the same output variable "
                            "without synchronization.",
                st_pattern=r"(\w+)\s*:=\s*TRUE",
                example_vulnerable='''// Task 1 (100ms cycle)
Motor := Condition1;
// Task 2 (50ms cycle, runs independently)
Motor := Condition2;  // Race condition''',
                example_fixed='''// Use a mediator variable and priority logic
VAR_OUTPUT
    Motor : BOOL;
END_VAR
Motor := Condition1 OR Condition2;  // Explicit arbitration''',
                iec_reference="IEC 61131-3 Part 3, Section 6.8",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-190",
                name="Integer Overflow in Arithmetic",
                severity="error",
                description="Arithmetic operations on INT/DINT without overflow checking "
                            "can wrap around, causing unexpected values.",
                st_pattern=r":=\s*\w+\s*[+\-*/]\s*\w+",
                example_vulnerable='''VAR
    Counter : INT;  // Range: -32768..32767
    Increment : INT := 1000;
END_VAR
Counter := Counter + Increment;  // May overflow''',
                example_fixed='''VAR
    Counter : INT;
    Increment : INT := 1000;
END_VAR
IF Counter <= (32767 - Increment) THEN
    Counter := Counter + Increment;
ELSE
    Counter := 32767;  // Saturate at max
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-369",
                name="Division by Zero",
                severity="critical",
                description="Division without checking for zero divisor causes PLC fault.",
                st_pattern=r":=\s*\w+\s*/\s*\w+",
                example_vulnerable='''VAR
    Result : REAL;
    Divisor : REAL;
END_VAR
Result := Numerator / Divisor;  // May divide by zero''',
                example_fixed='''VAR
    Result : REAL;
    Divisor : REAL;
END_VAR
IF ABS(Divisor) > 0.0001 THEN
    Result := Numerator / Divisor;
ELSE
    Result := 0.0;  // Safe default
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.5.3",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-478",
                name="Missing Default Case in CASE Statement",
                severity="warning",
                description="CASE statement without ELSE/default branch may leave outputs "
                            "in undefined state.",
                st_pattern=r"CASE\s+\w+\s+OF\s*\n[\s\S]*?END_CASE",
                example_vulnerable='''CASE State OF
    0: Output := Idle;
    1: Output := Running;
    2: Output := Stopped;
END_CASE;  // No ELSE — what if State is 3?''',
                example_fixed='''CASE State OF
    0: Output := Idle;
    1: Output := Running;
    2: Output := Stopped;
ELSE
    Output := ErrorState;  // Handle unexpected values
END_CASE;''',
                iec_reference="IEC 61131-3 Part 3, Section 7.5.3",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-798",
                name="Hardcoded Credentials",
                severity="critical",
                description="Hardcoded passwords, keys, or authentication tokens in ST code.",
                st_pattern=r"(?i)(password|secret|key|token)\s*:=\s*['\"]",
                example_vulnerable='''VAR
    AdminPassword : STRING := 'admin123';
    APIKey : STRING := 'sk-abc123xyz';
END_VAR''',
                example_fixed='''// Use system-level credential management
// Read from protected DB area or security module
VAR
    AdminPassword : STRING;  // Populated at runtime from secure storage
END_VAR''',
                iec_reference="IEC 62443-4-2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-676",
                name="Use of Potentially Dangerous Function",
                severity="warning",
                description="Using GOTO, unstructured jumps, or deprecated IL instructions.",
                st_pattern=r"GOTO\s+\w+",
                example_vulnerable='''IF Error THEN
    GOTO ErrorHandler;
END_IF;
// ... lots of code ...
ErrorHandler:
    // handle error''',
                example_fixed='''IF Error THEN
    HandleError();  // Use structured function call
ELSE
    // normal processing
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 7.5.5",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-457",
                name="Use of Uninitialized Variable",
                severity="error",
                description="Using a variable before it has been assigned a value. "
                            "On PLC runtimes, initial values may be undefined.",
                st_pattern=r":=\s*(\w+)",
                example_vulnerable='''VAR
    TempValue : INT;  // No initial value
    Result : INT;
END_VAR
Result := TempValue * 2;  // TempValue is undefined''',
                example_fixed='''VAR
    TempValue : INT := 0;  // Initialize
    Result : INT;
END_VAR
Result := TempValue * 2;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.4.2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-835",
                name="Infinite Loop",
                severity="critical",
                description="WHILE or REPEAT loop without proper exit condition "
                            "can hang the PLC scan cycle.",
                st_pattern=r"WHILE\s+TRUE\s+DO|REPEAT\s+.*\s+UNTIL\s+FALSE",
                example_vulnerable='''WHILE TRUE DO
    ProcessData();
    // No EXIT — infinite loop
END_WHILE;''',
                example_fixed='''WHILE Running AND (Timeout > 0) DO
    ProcessData();
    Timeout := Timeout - 1;
    IF ErrorCondition THEN
        EXIT;
    END_IF;
END_WHILE;''',
                iec_reference="IEC 61131-3 Part 3, Section 7.5.2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-628",
                name="Function Call with Incorrectly Specified Arguments",
                severity="error",
                description="Calling function blocks with wrong parameter types or order.",
                st_pattern=r"\w+\(.*:=.*\)",
                example_vulnerable='''VAR
    Timer1 : TON;
END_VAR
Timer1(IN := TRUE, PT := 100);  // PT should be TIME, not INT''',
                example_fixed='''VAR
    Timer1 : TON;
END_VAR
Timer1(IN := TRUE, PT := T#100MS);  // Correct TIME literal''',
                iec_reference="IEC 61131-3 Part 3, Section 7.2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-120",
                name="Buffer Copy without Checking Size",
                severity="error",
                description="String operations (CONCAT, INSERT, DELETE, REPLACE) without "
                            "length checking can overflow STRING buffers.",
                st_pattern=r"(?i)CONCAT\s*\(|INSERT\s*\(|REPLACE\s*\(",
                example_vulnerable='''VAR
    ShortStr : STRING[10];
    LongStr : STRING[100] := 'This is a very long string';
END_VAR
ShortStr := CONCAT(ShortStr, LongStr);  // May overflow''',
                example_fixed='''VAR
    ShortStr : STRING[10];
    LongStr : STRING[100] := 'This is a very long string';
    TempStr : STRING[110];
END_VAR
TempStr := CONCAT(ShortStr, LongStr);
IF LEN(TempStr) <= 10 THEN
    ShortStr := TempStr;
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.5.5",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-195",
                name="Signed to Unsigned Conversion Error",
                severity="warning",
                description="Implicit or explicit conversion between signed and unsigned "
                            "types can cause unexpected values.",
                st_pattern=r"(?i)(UINT|WORD|DWORD)\s*:=.*INT|INT\s*:=.*(?:UINT|WORD)",
                example_vulnerable='''VAR
    SignedVal : INT := -1;
    UnsignedVal : UINT;
END_VAR
UnsignedVal := UINT#SignedVal;  // Becomes 65535''',
                example_fixed='''VAR
    SignedVal : INT := -1;
    UnsignedVal : UINT;
END_VAR
IF SignedVal >= 0 THEN
    UnsignedVal := UINT#SignedVal;
ELSE
    UnsignedVal := 0;  // Clamp to safe value
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.2.3",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-665",
                name="Improper Initialization",
                severity="warning",
                description="Function block instances not properly initialized before use. "
                            "RETAIN variables may have stale values after warm restart.",
                st_pattern=r"(?i)VAR\s+RETAIN|VAR\s+INSTANCES",
                example_vulnerable='''VAR RETAIN
    ProductionCount : DINT;
    LastBatchID : DINT;
END_VAR
// After warm restart, LastBatchID has old value
// but ProductionCount may have been reset''',
                example_fixed='''VAR RETAIN
    ProductionCount : DINT;
    LastBatchID : DINT;
    InitFlag : BOOL;
END_VAR
IF NOT InitFlag THEN
    ProductionCount := 0;
    LastBatchID := 0;
    InitFlag := TRUE;
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.4.2",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-820",
                name="Missing Synchronization",
                severity="error",
                description="Accessing shared data from multiple tasks without proper "
                            "synchronization mechanisms.",
                st_pattern=r"VAR_GLOBAL|VAR_EXTERNAL",
                example_vulnerable='''// Global variable accessed from multiple tasks
VAR_GLOBAL
    SharedData : ARRAY[0..99] OF INT;
    WriteIndex : INT;
END_VAR
// Task 1 writes, Task 2 reads — no sync''',
                example_fixed='''VAR_GLOBAL
    SharedData : ARRAY[0..99] OF INT;
    WriteIndex : INT;
    DataReady : BOOL;  // Semaphore
END_VAR
// Writer: set DataReady after writing
// Reader: only read when DataReady, then clear it''',
                iec_reference="IEC 61131-3 Part 3, Section 6.8",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-284",
                name="Improper Access Control",
                severity="critical",
                description="No access control on critical safety functions. "
                            "Any program can write to safety outputs.",
                st_pattern=r"(?i)(safety|e_stop|emergency)\w*\s*:=\s*",
                example_vulnerable='''// Any program can control safety output
EmergencyStop := Sensor1 AND Sensor2;
SafetyValve := NOT OverPressure;''',
                example_fixed='''// Wrap in protected function block
FUNCTION_BLOCK SafetyController
VAR_INPUT
    Sensor1, Sensor2 : BOOL;
END_VAR
VAR_OUTPUT
    EmergencyStop : BOOL;
END_VAR
// Access-controlled safety logic
EmergencyStop := Sensor1 AND Sensor2;''',
                iec_reference="IEC 62443-3-3, IEC 61508",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-311",
                name="Missing Encryption of Sensitive Data",
                severity="error",
                description="Sensitive data (setpoints, recipes, passwords) transmitted "
                            "or stored without encryption.",
                st_pattern=r"(?i)(recipe|setpoint|parameter)\w*\s*:=\s*",
                example_vulnerable='''VAR
    RecipeTemp : REAL;  // Stored in plain text DB
    RecipePressure : REAL;
END_VAR
// Data readable via unencrypted S7 protocol''',
                example_fixed='''// Use encrypted communication channels
// Store sensitive data in protected memory areas
// Implement read-back verification''',
                iec_reference="IEC 62443-4-2, NIST 800-82",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-693",
                name="Protection Mechanism Failure",
                severity="critical",
                description="Watchdog timer not properly configured or disabled, "
                            "allowing program hang to go undetected.",
                st_pattern=r"(?i)watchdog|cycle_time|OB1.*time",
                example_vulnerable='''// OB1 with no watchdog monitoring
// Long-running code can hang without detection
IF ComplexCalculation THEN
    // This could take seconds
    ProcessLargeDataSet();
END_IF;''',
                example_fixed='''// Use proper watchdog and cycle monitoring
VAR
    CycleStart : TIME;
    CycleDuration : TIME;
    MaxCycleTime : TIME := T#150MS;
END_VAR
CycleStart := TIME();
// ... process ...
CycleDuration := TIME() - CycleStart;
IF CycleDuration > MaxCycleTime THEN
    WatchdogAlarm := TRUE;
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.8",
            ),
            PLCVulnerabilityPattern(
                cwe_id="CWE-754",
                name="Improper Check for Unusual Conditions",
                severity="warning",
                description="No error handling after operations that can fail "
                    "(type conversion, string operations, file access).",
                st_pattern=r"(?i)(INT_TO_|REAL_TO_|STRING_TO_)\w+",
                example_vulnerable='''VAR
    StrValue : STRING := 'abc';
    IntValue : INT;
END_VAR
IntValue := STRING_TO_INT(StrValue);  // May fail, no error check''',
                example_fixed='''VAR
    StrValue : STRING := 'abc';
    IntValue : INT;
    ConvOK : BOOL;
END_VAR
IntValue := STRING_TO_INT(StrValue);
// Always check conversion result
IF IntValue = 0 AND StrValue <> '0' THEN
    // Conversion failed
    LogError('Invalid integer conversion');
END_IF;''',
                iec_reference="IEC 61131-3 Part 3, Section 6.5",
            ),
        ]

    @staticmethod
    def get_review_guidelines() -> list[PLCReviewGuideline]:
        """Return PLCopen coding guidelines."""
        return [
            PLCReviewGuideline(
                rule_id="PLCOPEN-001",
                title="Use meaningful variable names",
                description="Variable names should describe their purpose. Use camelCase "
                            "or snake_case consistently. Prefix I/O variables with i_/o_.",
                category="style",
                severity="info",
                example_good='VAR\n    i_ConveyorSpeed : INT;\n    o_MotorRunning : BOOL;\nEND_VAR',
                example_bad='VAR\n    x : INT;\n    b1 : BOOL;\nEND_VAR',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-002",
                title="Initialize all variables",
                description="All variables should have explicit initial values. "
                            "RETAIN variables must be checked after warm restart.",
                category="reliability",
                severity="warning",
                example_good='VAR\n    Counter : INT := 0;\n    State : INT := STATE_IDLE;\nEND_VAR',
                example_bad='VAR\n    Counter : INT;\n    State : INT;\nEND_VAR',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-003",
                title="Avoid direct I/O access in program body",
                description="Use I/O mapping in dedicated blocks. Direct I/O addresses "
                            "in program code makes testing and maintenance difficult.",
                category="architecture",
                severity="warning",
                example_good='// In I/O mapping block\no_Motor := InternalMotorCmd;\n// In main program\nInternalMotorCmd := Start AND NOT Stop;',
                example_bad='%Q0.0 := Start AND NOT Stop;  // Direct I/O access',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-004",
                title="Limit function block size",
                description="Function blocks should not exceed 200 lines. "
                            "Split large blocks into smaller, testable units.",
                category="style",
                severity="info",
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-005",
                title="Use symbolic addressing",
                description="Prefer symbolic names over absolute addresses (%I0.0). "
                            "Makes code portable across hardware platforms.",
                category="portability",
                severity="info",
                example_good='VAR_INPUT\n    Sensor1 AT %I0.0 : BOOL;\nEND_VAR\nIF Sensor1 THEN',
                example_bad='IF %I0.0 THEN  // Absolute address in logic',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-006",
                title="Document all I/O variables",
                description="Every I/O variable must have a comment explaining its "
                            "physical connection and purpose.",
                category="documentation",
                severity="info",
                example_good='VAR_INPUT\n    i_EmergencyStop AT %I0.0 : BOOL; // E-Stop button, NC contact\nEND_VAR',
                example_bad='VAR_INPUT\n    i_EmergencyStop AT %I0.0 : BOOL;\nEND_VAR',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-007",
                title="Avoid magic numbers",
                description="Use named constants instead of literal numbers. "
                            "Makes code self-documenting and maintainable.",
                category="style",
                severity="warning",
                example_good='VAR CONSTANT\n    MAX_SPEED : INT := 1500;\nEND_VAR\nIF Speed > MAX_SPEED THEN',
                example_bad='IF Speed > 1500 THEN  // What is 1500?',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-008",
                title="Check array bounds",
                description="Always validate array indices before access. "
                            "Out-of-bounds access causes PLC fault.",
                category="safety",
                severity="error",
                example_good='IF (idx >= 0) AND (idx <= 99) THEN\n    Data[idx] := value;\nEND_IF;',
                example_bad='Data[idx] := value;  // No bounds check',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-009",
                title="Handle division by zero",
                description="Always check divisor before division operations. "
                            "Division by zero causes PLC fault.",
                category="safety",
                severity="error",
                example_good='IF ABS(divisor) > 0.001 THEN\n    result := numerator / divisor;\nEND_IF;',
                example_bad='result := numerator / divisor;  // May fault',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-010",
                title="Use CASE instead of nested IF-ELSIF",
                description="For state machines and multi-way branches, CASE is clearer "
                            "and more maintainable than deep IF-ELSIF chains.",
                category="readability",
                severity="info",
                example_good='CASE State OF\n    0: Idle();\n    1: Running();\n    2: Stopped();\nELSE\n    Error();\nEND_CASE;',
                example_bad='IF State = 0 THEN\n    Idle();\nELSIF State = 1 THEN\n    Running();\nELSIF State = 2 THEN\n    Stopped();\nEND_IF;',
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-011",
                title="Implement watchdog monitoring",
                description="Cyclic programs should monitor execution time. "
                            "Long-running code can indicate a hang condition.",
                category="safety",
                severity="warning",
            ),
            PLCReviewGuideline(
                rule_id="PLCOPEN-012",
                title="Limit nesting depth",
                description="Avoid nesting more than 4 levels deep. "
                            "Deep nesting is hard to read and error-prone.",
                category="readability",
                severity="warning",
                example_good='IF condition1 THEN\n    IF condition2 THEN\n        Process();\n    END_IF;\nEND_IF;',
                example_bad='IF a THEN\n    IF b THEN\n        IF c THEN\n            IF d THEN\n                IF e THEN\n                    // Too deep!\n                END_IF;\n            END_IF;\n        END_IF;\n    END_IF;\nEND_IF;',
            ),
        ]

    @staticmethod
    def get_few_shot_examples() -> list[FewShotExample]:
        """Return curated few-shot examples for LLM training."""
        return [
            FewShotExample(
                instruction="Review this Structured Text code for safety and correctness issues.",
                bad_code='''PROGRAM MotorControl
VAR
    StartButton : BOOL;
    StopButton : BOOL;
    Motor : BOOL;
    Speed : INT;
END_VAR

Motor := StartButton AND NOT StopButton;
Speed := 1500;
IF Speed > 2000 THEN
    Motor := FALSE;
END_IF;''',
                review_comment='''[
  {
    "file_path": "MotorControl.st",
    "line_start": 9,
    "line_end": 9,
    "severity": "warning",
    "category": "POTENTIAL_BUG",
    "title": "Magic number in speed assignment",
    "description": "Hardcoded value 1500 should be a named constant. Also, the speed limit check (2000) should use a constant.",
    "suggestion": "Define constants: VAR CONSTANT MAX_SPEED := 2000; NOMINAL_SPEED := 1500; END_VAR",
    "confidence": 0.95
  },
  {
    "file_path": "MotorControl.st",
    "line_start": 9,
    "line_end": 9,
    "severity": "warning",
    "category": "SAFETY",
    "title": "No interlock on motor start",
    "description": "Motor start depends only on button state. No safety interlock (e-stop, thermal relay, etc.) is checked.",
    "suggestion": "Add safety interlock: Motor := StartButton AND NOT StopButton AND SafetyOK AND NOT ThermalTrip;",
    "confidence": 0.9
  }
]''',
                fixed_code='''PROGRAM MotorControl
VAR CONSTANT
    NOMINAL_SPEED : INT := 1500;
    MAX_SPEED : INT := 2000;
END_VAR
VAR
    StartButton AT %I0.0 : BOOL;  // Start PB
    StopButton AT %I0.1 : BOOL;   // Stop PB (NC)
    SafetyOK AT %I0.2 : BOOL;     // Safety chain OK
    ThermalTrip AT %I0.3 : BOOL;  // Thermal relay
    Motor AT %Q0.0 : BOOL;        // Motor contactor
    Speed : INT;
END_VAR

Motor := StartButton AND NOT StopButton AND SafetyOK AND NOT ThermalTrip;
Speed := NOMINAL_SPEED;
IF Speed > MAX_SPEED THEN
    Motor := FALSE;
END_IF;''',
                rule_id="PLC-003,PLC-007",
                category="safety",
            ),
            FewShotExample(
                instruction="Review this ST code for potential bugs and IEC 61131-3 compliance.",
                bad_code='''FUNCTION_BLOCK ConveyorFB
VAR_INPUT
    Run : BOOL;
    Speed : INT;
END_VAR
VAR_OUTPUT
    MotorOut : BOOL;
    SpeedOut : INT;
END_VAR

MotorOut := Run;
SpeedOut := Speed;

IF Run THEN
    MotorOut := TRUE;
ELSE
    MotorOut := FALSE;
END_IF;''',
                review_comment='''[
  {
    "file_path": "ConveyorFB.st",
    "line_start": 12,
    "line_end": 16,
    "severity": "warning",
    "category": "POTENTIAL_BUG",
    "title": "Redundant output assignment (race condition)",
    "description": "MotorOut is assigned twice in the same cycle (line 12 and lines 13-16). The second assignment overwrites the first. This indicates confused logic.",
    "suggestion": "Remove the redundant assignment on line 12, keep only the IF-ELSE block.",
    "confidence": 0.95
  }
]''',
                fixed_code='''FUNCTION_BLOCK ConveyorFB
VAR_INPUT
    Run : BOOL;
    Speed : INT;
END_VAR
VAR_OUTPUT
    MotorOut : BOOL;
    SpeedOut : INT;
END_VAR

MotorOut := Run;
SpeedOut := Speed;''',
                rule_id="PLC-008",
                category="bugs",
            ),
            FewShotExample(
                instruction="Check this code for division safety and array bounds.",
                bad_code='''PROGRAM DataProcessor
VAR
    SensorData : ARRAY[0..99] OF REAL;
    Index : INT;
    Average : REAL;
    Sum : REAL;
    Count : INT;
END_VAR

Sum := 0;
FOR Index := 0 TO 100 DO
    Sum := Sum + SensorData[Index];
END_FOR;
Average := Sum / Count;''',
                review_comment='''[
  {
    "file_path": "DataProcessor.st",
    "line_start": 12,
    "line_end": 12,
    "severity": "critical",
    "category": "POTENTIAL_BUG",
    "title": "Array index out of bounds",
    "description": "FOR loop goes to 100 but array is 0..99. Index 100 is out of bounds, causing PLC fault.",
    "suggestion": "Change loop to: FOR Index := 0 TO 99 DO",
    "confidence": 0.99
  },
  {
    "file_path": "DataProcessor.st",
    "line_start": 15,
    "line_end": 15,
    "severity": "critical",
    "category": "POTENTIAL_BUG",
    "title": "Division by zero",
    "description": "Count is never assigned a value, so it defaults to 0. Division by zero will cause PLC fault.",
    "suggestion": "Initialize Count and check before division: IF Count > 0 THEN Average := Sum / Count; END_IF;",
    "confidence": 0.99
  }
]''',
                fixed_code='''PROGRAM DataProcessor
VAR
    SensorData : ARRAY[0..99] OF REAL;
    Index : INT;
    Average : REAL := 0.0;
    Sum : REAL := 0.0;
    Count : INT := 0;
END_VAR

Sum := 0.0;
Count := 0;
FOR Index := 0 TO 99 DO
    Sum := Sum + SensorData[Index];
    Count := Count + 1;
END_FOR;
IF Count > 0 THEN
    Average := Sum / Count;
END_IF;''',
                rule_id="PLC-004,PLC-006",
                category="bugs",
            ),
        ]

    @staticmethod
    def get_standard_references() -> dict[str, str]:
        """Return IEC 61131-3 standard section references mapped to topics."""
        return {
            "data_types": "IEC 61131-3 Part 3, Section 6.2 — Data types and their properties",
            "variables": "IEC 61131-3 Part 3, Section 6.4 — Variable declarations and initializations",
            "expressions": "IEC 61131-3 Part 3, Section 6.5 — Expressions and operators",
            "statements": "IEC 61131-3 Part 3, Section 7 — Statements (IF, CASE, FOR, WHILE, etc.)",
            "functions": "IEC 61131-3 Part 3, Section 7.2 — Function calls",
            "function_blocks": "IEC 61131-3 Part 3, Section 7.3 — Function block calls",
            "programs": "IEC 61131-3 Part 3, Section 7.4 — Program organization units",
            "tasks": "IEC 61131-3 Part 3, Section 6.8 — Tasks and concurrency",
            "configurations": "IEC 61131-3 Part 3, Section 6.9 — Configurations and resources",
            "arrays": "IEC 61131-3 Part 3, Section 6.5.4 — Array indexing",
            "strings": "IEC 61131-3 Part 3, Section 6.5.5 — String operations",
            "type_conversion": "IEC 61131-3 Part 3, Section 6.2.3 — Type conversion functions",
            "safety": "IEC 61508 — Functional safety of electrical/electronic systems",
            "security": "IEC 62443 — Industrial automation and control systems security",
            "plcopen": "PLCopen — IEC 61131-3 coding guidelines version 2.0",
        }

    @staticmethod
    def get_vendor_quirks() -> dict[str, list[str]]:
        """Return vendor-specific quirks and gotchas."""
        return {
            "siemens": [
                "S7-1200/1500 uses SimaticML XML for source storage",
                "TIA Portal adds implicit type conversions that other vendors reject",
                "SCL (Structured Control Language) is Siemens' ST dialect with minor differences",
                "IEC timers (TON, TOF) have different default behavior than Siemens S5 timers",
                "DB (Data Block) variables are automatically retained",
                "OB1 cycle time watchdog defaults to 150ms on S7-1500",
            ],
            "beckhoff": [
                "TwinCAT 3 uses .tsm (TwinCAT Solution Manager) project format",
                "TcPOU XML contains CDATA blocks for source code",
                "Supports both IEC and C++ (via TcCOM) in same project",
                "Instance declarations use different syntax than standard IEC",
                "AT addressing uses %I, %Q, %M prefix (not %%I like some vendors)",
            ],
            "codesys": [
                "CODESYS V3 is used by WAGO, Schneider, ABB AC500, Bosch Rexroth, Phoenix Contact",
                "Project file is a structured text XML with CDATA for source code",
                "Supports all 5 IEC languages plus Instruction List (IL)",
                "Function block instances are declared differently from standard IEC",
                "Visualization elements may be embedded in project file",
            ],
            "rockwell": [
                "Studio 5000 uses L5X XML format for import/export",
                "Tag-based addressing (not variable-based like IEC)",
                "RLL (Ladder) uses XIC/XIO/OTE/OTL/OTU instructions",
                "Programs are organized in Tasks → Programs → Routines hierarchy",
                "Controller-scoped vs Program-scoped tags (similar to global/local)",
            ],
        }
