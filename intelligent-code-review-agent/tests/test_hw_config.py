"""Tests for the hardware configuration parser and rules checker."""
import pytest
from src.plc.hw_config import (
    HWConfigParser, HWConfigRulesChecker, HardwareConfig, HWRuleViolation,
    CPUConfig, IOModule, NetworkConfig, SafetyConfig,
)


class TestHWConfigParser:
    """Test HWConfig XML parsing."""

    def test_is_hwconfig_with_siemens_root(self):
        xml = '<Engineering><Station Name="PLC_1"><CPU Model="S7-1500"/></Station></Engineering>'
        assert HWConfigParser.is_hwconfig_string(xml) is True

    def test_is_hwconfig_with_hw_root(self):
        xml = '<HW><Device Name="PLC_1"><Controller Model="S7-1200"/></Device></HW>'
        assert HWConfigParser.is_hwconfig_string(xml) is True

    def test_is_hwconfig_false_for_plain_xml(self):
        xml = '<root><element>text</element></root>'
        assert HWConfigParser.is_hwconfig_string(xml) is False

    def test_parse_cpu_basic(self):
        xml = '''<Engineering>
            <CPU Model="S7-1500" ArticleNumber="6ES7 516-3AN02-0AB0" FirmwareVersion="2.8.3">
                <ProtectionLevel>2</ProtectionLevel>
                <CycleWatchdog>150</CycleWatchdog>
                <IPAddress>192.168.1.1</IPAddress>
            </CPU>
        </Engineering>'''
        config = HWConfigParser.parse_string(xml)
        assert config is not None
        assert config.cpu.model == "S7-1500"
        assert config.cpu.article_number == "6ES7 516-3AN02-0AB0"
        assert config.cpu.firmware_version == "2.8.3"
        assert config.cpu.protection_level == 2
        assert config.cpu.cycle_watchdog_ms == 150
        assert config.cpu.ip_address == "192.168.1.1"

    def test_parse_safety_cpu(self):
        xml = '<Engineering><CPU Model="S7-1500F CPU 1516F-3 PN/DP" ArticleNumber="6ES7 516-3FN02-0AB0"><SafetyConfiguration SafetyLevel="SIL3"><SafetyProgram>SafeMain</SafetyProgram><Password>secret</Password></SafetyConfiguration></CPU></Engineering>'
        config = HWConfigParser.parse_string(xml)
        assert config is not None
        assert config.cpu.is_safety_cpu is True
        assert config.safety.f_cpu_enabled is True
        assert config.safety.safety_level == "SIL3"
        assert "SafeMain" in config.safety.safety_programs
        assert config.safety.password_level_1 == "secret"

    def test_parse_io_modules(self):
        xml = '''<Engineering>
            <Module Name="DI 16x24VDC" Slot="1" Type="DI" ArticleNumber="6ES7 521-1BH50"/>
            <Module Name="F-DQ 8x24VDC" Slot="2" Type="DO" ArticleNumber="6ES7 526-1BF00"/>
        </Engineering>'''
        config = HWConfigParser.parse_string(xml)
        assert config is not None
        assert len(config.io_modules) == 2
        assert config.io_modules[0].slot == 1
        assert config.io_modules[0].module_type == "DI"

    def test_parse_network(self):
        xml = '''<Engineering>
            <NetworkInterface Name="X1" Protocol="PROFINET">
                <IPAddress>10.0.0.1</IPAddress>
                <SubnetMask>255.255.255.0</SubnetMask>
                <DCPName>PLC_1</DCPName>
            </NetworkInterface>
        </Engineering>'''
        config = HWConfigParser.parse_string(xml)
        assert config is not None
        assert len(config.networks) == 1
        assert config.networks[0].ip_address == "10.0.0.1"
        assert config.networks[0].dcp_name == "PLC_1"

    def test_parse_web_server(self):
        xml = '''<Engineering>
            <CPU Model="S7-1500">
                <WebServer Port="80">true</WebServer>
            </CPU>
        </Engineering>'''
        config = HWConfigParser.parse_string(xml)
        assert config is not None
        assert config.cpu.web_server_enabled is True
        assert config.cpu.web_server_port == 80

    def test_parse_empty_xml(self):
        config = HWConfigParser.parse_string("<Engineering/>")
        assert config is not None
        assert config.cpu.model == ""

    def test_parse_invalid_xml(self):
        config = HWConfigParser.parse_string("not xml")
        assert config is None


class TestHWConfigRulesChecker:
    """Test hardware configuration rules."""

    def _make_config(self, **kwargs) -> HardwareConfig:
        """Helper to create a HardwareConfig with overrides."""
        cpu = CPUConfig(
            model=kwargs.get("model", "S7-1500"),
            firmware_version=kwargs.get("firmware", "2.9"),
            article_number=kwargs.get("article", "6ES7 516-3AN02-0AB0"),
            protection_level=kwargs.get("protection", 2),
            cycle_watchdog_ms=kwargs.get("watchdog", 150),
            web_server_enabled=kwargs.get("web_server", False),
            web_server_port=kwargs.get("web_port", 443),
            is_safety_cpu=kwargs.get("is_safety_cpu", False),
        )
        safety = SafetyConfig(
            f_cpu_enabled=kwargs.get("f_cpu", False),
            safety_level=kwargs.get("safety_level", ""),
            safety_programs=kwargs.get("safety_programs", []),
            password_level_1=kwargs.get("safety_password", ""),
        )
        return HardwareConfig(cpu=cpu, safety=safety, io_modules=kwargs.get("io_modules", []),
                              networks=kwargs.get("networks", []))

    def test_no_violations_clean_config(self):
        config = self._make_config()
        violations = HWConfigRulesChecker.check(config)
        # Clean config should have no violations
        assert len(violations) == 0

    def test_hw001_vulnerable_firmware(self):
        config = self._make_config(model="S7-1500", firmware="2.8.3")
        violations = HWConfigRulesChecker.check(config)
        hw001 = [v for v in violations if v.rule_id == "HW-001"]
        assert len(hw001) > 0
        assert hw001[0].severity == "critical"

    def test_hw002_no_protection(self):
        config = self._make_config(protection=0)
        violations = HWConfigRulesChecker.check(config)
        hw002 = [v for v in violations if v.rule_id == "HW-002"]
        assert len(hw002) == 1
        assert hw002[0].severity == "error"

    def test_hw003_watchdog_disabled(self):
        config = self._make_config(watchdog=0)
        violations = HWConfigRulesChecker.check(config)
        hw003 = [v for v in violations if v.rule_id == "HW-003"]
        assert len(hw003) == 1
        assert "disabled" in hw003[0].description.lower()

    def test_hw003_watchdog_too_long(self):
        config = self._make_config(watchdog=1000)
        violations = HWConfigRulesChecker.check(config)
        hw003 = [v for v in violations if v.rule_id == "HW-003"]
        assert len(hw003) == 1
        assert hw003[0].severity == "warning"

    def test_hw004_safety_io_no_redundancy(self):
        io = IOModule(module_name="F-DQ 8x24VDC", is_safety=True, is_redundant=False)
        config = self._make_config(io_modules=[io])
        violations = HWConfigRulesChecker.check(config)
        hw004 = [v for v in violations if v.rule_id == "HW-004"]
        assert len(hw004) == 1

    def test_hw005_safety_cpu_no_program(self):
        config = self._make_config(is_safety_cpu=True, f_cpu=False)
        violations = HWConfigRulesChecker.check(config)
        hw005 = [v for v in violations if v.rule_id == "HW-005"]
        assert len(hw005) >= 1

    def test_hw006_profinet_no_port_security(self):
        net = NetworkConfig(protocol="PROFINET", interface_name="X1", port_security_enabled=False)
        config = self._make_config(networks=[net])
        violations = HWConfigRulesChecker.check(config)
        hw006 = [v for v in violations if v.rule_id == "HW-006"]
        assert len(hw006) == 1

    def test_hw007_safety_no_password(self):
        config = self._make_config(f_cpu=True, safety_programs=["Prog1"], safety_password="")
        violations = HWConfigRulesChecker.check(config)
        hw007 = [v for v in violations if v.rule_id == "HW-007"]
        assert len(hw007) == 1
        assert hw007[0].severity == "critical"

    def test_hw008_web_server_http(self):
        config = self._make_config(web_server=True, web_port=80)
        violations = HWConfigRulesChecker.check(config)
        hw008 = [v for v in violations if v.rule_id == "HW-008"]
        assert len(hw008) == 1
        assert "HTTP" in hw008[0].description

    def test_hw009_s7comm_no_encryption(self):
        net = NetworkConfig(protocol="S7comm", interface_name="X1", encryption_enabled=False)
        config = self._make_config(networks=[net])
        violations = HWConfigRulesChecker.check(config)
        hw009 = [v for v in violations if v.rule_id == "HW-009"]
        assert len(hw009) == 1

    def test_hw012_article_mismatch(self):
        config = self._make_config(model="S7-1200", article="6ES7 516-3AN02-0AB0")
        violations = HWConfigRulesChecker.check(config)
        hw012 = [v for v in violations if v.rule_id == "HW-012"]
        assert len(hw012) == 1

    def test_profinet_with_port_security_ok(self):
        net = NetworkConfig(protocol="PROFINET", port_security_enabled=True)
        config = self._make_config(networks=[net])
        violations = HWConfigRulesChecker.check(config)
        hw006 = [v for v in violations if v.rule_id == "HW-006"]
        assert len(hw006) == 0


class TestHWRuleViolation:
    """Test HWRuleViolation model."""

    def test_valid_violation(self):
        v = HWRuleViolation(
            rule_id="HW-001", rule_name="Test", severity="warning", description="Test desc"
        )
        assert v.rule_id == "HW-001"
        assert v.severity == "warning"

    def test_with_component_and_suggestion(self):
        v = HWRuleViolation(
            rule_id="HW-002", rule_name="Test", severity="error",
            description="Test", component="CPU", suggestion="Fix it"
        )
        assert v.component == "CPU"
        assert v.suggestion == "Fix it"
