"""Tests for the FBD-to-ST converter."""
import pytest
from src.plc.fbd_converter import FBDConverter, FBDConversion


class TestFBDConverter:
    """Test FBD XML to ST conversion."""

    def test_simple_add_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="ADD"><InputPin Name="IN1">SensorA</InputPin><InputPin Name="IN2">100</InputPin><OutputPin Name="OUT">Result</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "Result" in result.st_code
        assert "SensorA" in result.st_code
        assert "100" in result.st_code
        assert "+" in result.st_code
        assert len(result.warnings) == 0

    def test_comparison_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="GT"><InputPin Name="IN1">Temp</InputPin><InputPin Name="IN2">80</InputPin><OutputPin Name="OUT">Alarm</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "Alarm" in result.st_code
        assert ">" in result.st_code
        assert "Temp" in result.st_code
        assert "80" in result.st_code

    def test_not_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="NOT"><InputPin Name="IN">Sensor</InputPin><OutputPin Name="OUT">Inverted</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "NOT" in result.st_code
        assert "Inverted" in result.st_code

    def test_chained_blocks(self):
        """Output of one block feeds into another."""
        xml = '<FBD><Network Number="1"><Block ID="1" Type="ADD"><InputPin Name="IN1">A</InputPin><InputPin Name="IN2">B</InputPin><OutputPin Name="OUT">sum</OutputPin></Block><Block ID="2" Type="GT"><InputPin Name="IN1">sum</InputPin><InputPin Name="IN2">100</InputPin><OutputPin Name="OUT">over</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "sum" in result.st_code
        assert "over" in result.st_code
        # ADD should come before GT in output
        add_pos = result.st_code.find("+")
        gt_pos = result.st_code.find(">")
        assert add_pos < gt_pos

    def test_timer_function_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="TON" InstanceName="MyTimer"><InputPin Name="IN">Start</InputPin><InputPin Name="PT">T#5S</InputPin><OutputPin Name="Q">Running</OutputPin><OutputPin Name="ET">Elapsed</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "MyTimer" in result.st_code
        assert "IN :=" in result.st_code
        assert "PT :=" in result.st_code
        assert "T#5S" in result.st_code
        assert ".Q" in result.st_code
        assert ".ET" in result.st_code

    def test_counter_function_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="CTU" InstanceName="Counter1"><InputPin Name="CU">Pulse</InputPin><InputPin Name="PV">10</InputPin><OutputPin Name="Q">Done</OutputPin><OutputPin Name="CV">Count</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "Counter1" in result.st_code
        assert "CU :=" in result.st_code
        assert ".Q" in result.st_code
        assert ".CV" in result.st_code

    def test_move_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="MOVE"><InputPin Name="IN">SourceVar</InputPin><OutputPin Name="OUT">DestVar</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "DestVar" in result.st_code
        assert "SourceVar" in result.st_code
        assert ":=" in result.st_code

    def test_type_conversion(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="INT_TO_REAL"><InputPin Name="IN">IntVal</InputPin><OutputPin Name="OUT">RealVal</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "INT_TO_REAL" in result.st_code
        assert "RealVal" in result.st_code

    def test_multi_input_and(self):
        """AND with 3 inputs."""
        xml = '<FBD><Network Number="1"><Block ID="1" Type="AND"><InputPin Name="IN1">A</InputPin><InputPin Name="IN2">B</InputPin><InputPin Name="IN3">C</InputPin><OutputPin Name="OUT">AllOK</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "AND" in result.st_code
        assert "AllOK" in result.st_code

    def test_arithmetic_operators(self):
        for op, expected in [("SUB", "-"), ("MUL", "*"), ("DIV", "/"), ("MOD", "MOD")]:
            xml = f'<FBD><Network Number="1"><Block ID="1" Type="{op}"><InputPin Name="IN1">A</InputPin><InputPin Name="IN2">B</InputPin><OutputPin Name="OUT">Result</OutputPin></Block></Network></FBD>'
            result = FBDConverter.convert_xml_to_st(xml)
            assert expected in result.st_code, f"Expected '{expected}' for {op} block"

    def test_comparison_operators(self):
        for op, expected in [("GE", ">="), ("LT", "<"), ("LE", "<="), ("EQ", "="), ("NE", "<>")]:
            xml = f'<FBD><Network Number="1"><Block ID="1" Type="{op}"><InputPin Name="IN1">A</InputPin><InputPin Name="IN2">B</InputPin><OutputPin Name="OUT">Result</OutputPin></Block></Network></FBD>'
            result = FBDConverter.convert_xml_to_st(xml)
            assert expected in result.st_code, f"Expected '{expected}' for {op} block"

    def test_time_literal_preserved(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="TON" InstanceName="T1"><InputPin Name="IN">Run</InputPin><InputPin Name="PT">T#10S</InputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "T#10S" in result.st_code

    def test_boolean_literal(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="AND"><InputPin Name="IN1">TRUE</InputPin><InputPin Name="IN2">Flag</InputPin><OutputPin Name="OUT">Result</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "TRUE" in result.st_code

    def test_empty_xml(self):
        result = FBDConverter.convert_xml_to_st("<FBD></FBD>")
        assert result.st_code == ""
        assert len(result.warnings) > 0

    def test_invalid_xml(self):
        result = FBDConverter.convert_xml_to_st("not xml")
        assert result.st_code == ""
        assert "Failed to parse" in result.warnings[0]

    def test_has_fbd_marker(self):
        assert FBDConverter.has_fbd_marker("[FBD_XML:<FBD></FBD>]")
        assert not FBDConverter.has_fbd_marker("[LD_XML:<Ladder></Ladder>]")
        assert not FBDConverter.has_fbd_marker("just plain code")

    def test_extract_and_convert_marker(self):
        source = 'PROGRAM Main\n[FBD_XML:<FBD><Network Number="1"><Block ID="1" Type="ADD"><InputPin Name="IN1">X</InputPin><InputPin Name="IN2">1</InputPin><OutputPin Name="OUT">Y</OutputPin></Block></Network></FBD>]\nEND_PROGRAM'
        result = FBDConverter.extract_and_convert(source)
        assert "Y" in result.st_code
        assert "FBD" in result.st_code

    def test_no_networks(self):
        xml = '<FBD><SomethingElse/></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert result.st_code == ""

    def test_wire_based_connections(self):
        """Test wire-based block connections (not inline pin variables)."""
        xml = '<FBD><Network Number="1"><Block ID="1" Type="ADD"><InputPin Name="IN1">A</InputPin><InputPin Name="IN2">B</InputPin><OutputPin Name="OUT"/></Block><Block ID="2" Type="MUL"><InputPin Name="IN1"/><InputPin Name="IN2">C</InputPin><OutputPin Name="OUT">Final</OutputPin></Block><Wire><SourceBlock>1</SourceBlock><SourcePin>OUT</SourcePin><TargetBlock>2</TargetBlock><TargetPin>IN1</TargetPin></Wire></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "Final" in result.st_code
        assert len(result.warnings) == 0

    def test_generic_unknown_block(self):
        """Unknown block type generates a function call."""
        xml = '<FBD><Network Number="1"><Block ID="1" Type="MY_CUSTOM_FB" InstanceName="CustomInst"><InputPin Name="IN1">X</InputPin><OutputPin Name="OUT1">Y</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "CustomInst" in result.st_code
        assert "IN1 :=" in result.st_code

    def test_sel_block(self):
        xml = '<FBD><Network Number="1"><Block ID="1" Type="SEL"><InputPin Name="G">Switch</InputPin><InputPin Name="IN0">ValA</InputPin><InputPin Name="IN1">ValB</InputPin><OutputPin Name="OUT">Selected</OutputPin></Block></Network></FBD>'
        result = FBDConverter.convert_xml_to_st(xml)
        assert "SEL" in result.st_code
        assert "Selected" in result.st_code


class TestFBDConversionModel:
    """Test the FBDConversion model."""

    def test_valid_conversion(self):
        conv = FBDConversion(st_code="x := 1;", source_networks=[1])
        assert conv.st_code == "x := 1;"
        assert conv.source_networks == [1]
        assert conv.warnings == []

    def test_conversion_with_warnings(self):
        conv = FBDConversion(st_code="", warnings=["bad xml"])
        assert conv.st_code == ""
        assert len(conv.warnings) == 1
