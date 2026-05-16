"""Tests for PLC project file support helpers."""

from pathlib import Path

from src.plc.file_support import (
    extract_structured_text,
    has_plc_project_extension,
    is_plc_project_file,
)


def test_plc_project_extensions():
    assert has_plc_project_extension("program.xml")
    assert has_plc_project_extension("controller.L5X")
    assert has_plc_project_extension("project.smc2")
    assert not has_plc_project_extension("program.st")


def test_detect_and_extract_rockwell_l5x(tmp_path: Path):
    l5x = tmp_path / "controller.L5X"
    l5x.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<RSLogix5000Content>
  <Controller Name="Demo">
    <Programs>
      <Program Name="MainProgram">
        <Routines>
          <Routine Name="MainRoutine" Type="ST">
            <STContent>
              <Line Number="0">Motor := StartButton;</Line>
            </STContent>
          </Routine>
        </Routines>
      </Program>
    </Programs>
  </Controller>
</RSLogix5000Content>
""",
        encoding="utf-8",
    )

    assert is_plc_project_file(str(l5x))
    source = extract_structured_text(str(l5x))
    assert source is not None
    assert "Motor := StartButton;" in source
