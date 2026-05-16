"""Tests for the PLC fine-tuning data pipeline."""
import json
import os
import tempfile
import pytest
from src.plc.finetune.domain_context import DomainContext, PLCVulnerabilityPattern, FewShotExample
from src.plc.finetune.prompt_builder import PLCPromptBuilder
from src.plc.finetune.dataset_generator import DatasetGenerator, FineTuneExample


class TestDomainContext:
    """Test the domain knowledge base."""

    def test_vulnerability_patterns_count(self):
        patterns = DomainContext.get_vulnerability_patterns()
        assert len(patterns) >= 20

    def test_vulnerability_patterns_have_cwe(self):
        patterns = DomainContext.get_vulnerability_patterns()
        for p in patterns:
            assert p.cwe_id.startswith("CWE-"), f"{p.name} missing CWE ID"
            assert p.example_vulnerable, f"{p.name} missing vulnerable example"
            assert p.example_fixed, f"{p.name} missing fixed example"

    def test_vulnerability_patterns_valid_severity(self):
        patterns = DomainContext.get_vulnerability_patterns()
        valid = {"critical", "error", "warning", "info"}
        for p in patterns:
            assert p.severity in valid, f"{p.name} has invalid severity: {p.severity}"

    def test_review_guidelines_count(self):
        guidelines = DomainContext.get_review_guidelines()
        assert len(guidelines) >= 10

    def test_review_guidelines_have_ids(self):
        guidelines = DomainContext.get_review_guidelines()
        for g in guidelines:
            assert g.rule_id.startswith("PLCOPEN-")
            assert g.title
            assert g.description

    def test_few_shot_examples_count(self):
        examples = DomainContext.get_few_shot_examples()
        assert len(examples) >= 3

    def test_few_shot_examples_have_all_fields(self):
        examples = DomainContext.get_few_shot_examples()
        for ex in examples:
            assert ex.instruction
            assert ex.bad_code
            assert ex.review_comment
            assert ex.fixed_code
            # Verify review_comment is valid JSON
            parsed = json.loads(ex.review_comment)
            assert isinstance(parsed, list)

    def test_standard_references(self):
        refs = DomainContext.get_standard_references()
        assert len(refs) >= 10
        for topic, ref in refs.items():
            assert "IEC" in ref or "PLCopen" in ref or "NIST" in ref

    def test_vendor_quirks(self):
        quirks = DomainContext.get_vendor_quirks()
        assert "siemens" in quirks
        assert "beckhoff" in quirks
        assert "codesys" in quirks
        assert "rockwell" in quirks


class TestPLCPromptBuilder:
    """Test prompt building."""

    def test_system_prompt_general(self):
        builder = PLCPromptBuilder()
        prompt = builder.build_system_prompt("general")
        assert "IEC 61131-3" in prompt
        assert "Structured Text" in prompt
        assert "cyclically" in prompt

    def test_system_prompt_safety(self):
        builder = PLCPromptBuilder()
        prompt = builder.build_system_prompt("safety")
        assert "emergency stop" in prompt.lower() or "safety" in prompt.lower()
        assert "SIL" in prompt

    def test_system_prompt_security(self):
        builder = PLCPromptBuilder()
        prompt = builder.build_system_prompt("security")
        assert "credential" in prompt.lower() or "security" in prompt.lower()

    def test_few_shot_prompt(self):
        builder = PLCPromptBuilder()
        code = "Motor := Start;"
        prompt = builder.build_few_shot_prompt(code)
        assert code in prompt
        assert "Example" in prompt
        assert "JSON" in prompt

    def test_chain_of_thought_prompt(self):
        builder = PLCPromptBuilder()
        code = "Result := A / B;"
        prompt = builder.build_chain_of_thought_prompt(code)
        assert code in prompt
        assert "step by step" in prompt.lower() or "analysis" in prompt.lower()

    def test_vulnerability_prompt(self):
        builder = PLCPromptBuilder()
        code = "Data[idx] := 42;"
        prompt = builder.build_vulnerability_prompt(code, "buffer")
        assert code in prompt
        assert "CWE-" in prompt

    def test_safety_review_prompt(self):
        builder = PLCPromptBuilder()
        code = "Motor := Run;"
        prompt = builder.build_safety_review_prompt(code, "SIL2")
        assert "SIL2" in prompt

    def test_get_all_prompts(self):
        builder = PLCPromptBuilder()
        prompts = builder.get_all_prompts()
        assert "system" in prompts
        assert "system_safety" in prompts
        assert "system_security" in prompts


class TestDatasetGenerator:
    """Test dataset generation."""

    def test_generate_from_rules(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_rules()
        assert len(examples) > 0
        for ex in examples:
            assert ex.instruction
            assert ex.input
            assert ex.output
            # Output should be valid JSON
            parsed = json.loads(ex.output)
            assert isinstance(parsed, list)

    def test_generate_from_vulnerability_db(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_vulnerability_db()
        assert len(examples) > 0
        # Should have both vulnerable and clean examples
        severities = {ex.metadata.get("severity") for ex in examples}
        assert "clean" in severities

    def test_generate_from_few_shot(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_few_shot()
        assert len(examples) >= 3

    def test_generate_all(self):
        gen = DatasetGenerator()
        examples = gen.generate_all()
        assert len(examples) > 0
        stats = gen.get_stats(examples)
        assert stats.total_examples == len(examples)

    def test_split_dataset(self):
        gen = DatasetGenerator()
        examples = gen.generate_all()
        train, val, test = gen.split_dataset(examples, 0.7, 0.15)
        assert len(train) > 0
        assert len(val) > 0
        assert len(test) > 0
        assert len(train) + len(val) + len(test) == len(examples)

    def test_export_jsonl(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_rules()[:3]
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
            path = f.name
        try:
            gen.export_jsonl(examples, path)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 3
            for line in lines:
                record = json.loads(line)
                assert "messages" in record
                assert len(record["messages"]) == 3
        finally:
            os.unlink(path)

    def test_export_alpaca(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_rules()[:2]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            gen.export_alpaca(examples, path)
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
            assert len(records) == 2
            for r in records:
                assert "instruction" in r
                assert "input" in r
                assert "output" in r
        finally:
            os.unlink(path)

    def test_export_sharegpt(self):
        gen = DatasetGenerator()
        examples = gen.generate_from_rules()[:2]
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            gen.export_sharegpt(examples, path)
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
            assert len(records) == 2
            for r in records:
                assert "conversations" in r
                assert len(r["conversations"]) == 3
        finally:
            os.unlink(path)

    def test_get_stats(self):
        gen = DatasetGenerator()
        examples = gen.generate_all()
        stats = gen.get_stats(examples)
        assert stats.total_examples > 0
        assert len(stats.by_severity) > 0
        assert len(stats.by_source) > 0


class TestFineTuneExample:
    """Test the FineTuneExample model."""

    def test_valid_example(self):
        ex = FineTuneExample(
            instruction="Review this code",
            input="```st\nMotor := Run;\n```",
            output="[]",
        )
        assert ex.instruction == "Review this code"
        assert ex.metadata == {}

    def test_with_metadata(self):
        ex = FineTuneExample(
            instruction="Review",
            input="code",
            output="[]",
            metadata={"rule_id": "PLC-001", "severity": "warning"},
        )
        assert ex.metadata["rule_id"] == "PLC-001"
