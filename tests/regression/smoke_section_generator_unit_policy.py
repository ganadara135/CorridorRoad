# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Section generator unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_section_generator_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_assembly_template import AssemblyTemplate, ensure_assembly_template_properties
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects.obj_section_set import SectionSet, ensure_section_set_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_section_generator import SectionGeneratorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRSectionGeneratorUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "m"

        sec = doc.addObject("Part::FeaturePython", "SectionSet")
        SectionSet(sec)
        ensure_section_set_properties(sec)
        sec.StartStation = 25.0
        sec.EndStation = 100.0
        sec.Interval = 20.0
        sec.StationText = "0.000000, 20.000000, 37.500000"
        sec.StructureTransitionDistance = 5.0

        asm = doc.addObject("Part::FeaturePython", "AssemblyTemplate")
        AssemblyTemplate(asm)
        ensure_assembly_template_properties(asm)
        asm.LeftSideWidth = 3.0
        asm.RightSideWidth = 4.0
        asm.UseLeftBench = True
        asm.LeftBenchRows = ["drop=1.000000|width=1.500000|slope=0.000000|post=50.000000"]
        asm.DaylightSearchStep = 1.0
        asm.DaylightMaxSearchWidth = 200.0
        asm.DaylightMaxWidthDelta = 6.0

        panel = SectionGeneratorTaskPanel()

        _assert(panel.spin_start.suffix().strip() == "m", "Section start station should show meter suffix")
        _assert(abs(float(panel.spin_start.value()) - 25.0) < 1.0e-6, "Start station should display as 25 m")
        _assert(abs(float(panel.spin_end.value()) - 100.0) < 1.0e-6, "End station should display as 100 m")
        _assert(abs(float(panel.spin_itv.value()) - 20.0) < 1.0e-6, "Interval should display as 20 m")
        _assert(abs(float(panel.spin_struct_transition.value()) - 5.0) < 1.0e-6, "Structure transition should display as 5 m")
        _assert(abs(float(panel.spin_side_w_left.value()) - 3.0) < 1.0e-6, "Left side width should display as 3 m")
        _assert(abs(float(panel.spin_side_w_right.value()) - 4.0) < 1.0e-6, "Right side width should display as 4 m")
        _assert(abs(float(panel.spin_day_step.value()) - 1.0) < 1.0e-6, "Daylight search step should display as 1 m")
        _assert(abs(float(panel.spin_day_max_w.value()) - 200.0) < 1.0e-6, "Daylight max width should display as 200 m")
        _assert(abs(float(panel.spin_day_max_delta.value()) - 6.0) < 1.0e-6, "Daylight max delta should display as 6 m")
        _assert(panel.tbl_left_bench_rows.horizontalHeaderItem(0).text().endswith("(m)"), "Bench table header should show meter unit")
        _assert(panel.txt_manual.toPlainText() == "0.000, 20.000, 37.500", "Manual station text should be formatted in display units")
        _assert("Display unit: m" in str(panel.lbl_info.text() or ""), "Section generator info should report display unit")
        _assert("Current range inputs: start=25.000, end=100.000, interval=20.000 m" in str(panel.lbl_info.text() or ""), "Section generator info should report display-unit range inputs")

        sec.StationValues = [25.0, 45.0, 65.0, 85.0]
        completion_summary = panel._completion_summary_text(sec)
        _assert("Display unit: m" in completion_summary, "Section generator completion summary should report display unit")
        _assert("Range input (display): 25.000 -> 100.000 @ 20.000 m" in completion_summary, "Section generator completion summary should report display-range values")
        _assert("Resolved stations: 4" in completion_summary, "Section generator completion summary should report resolved station count")

        panel.spin_side_w_left.setValue(5.0)
        panel.spin_side_w_right.setValue(6.0)
        panel.spin_day_step.setValue(2.0)
        panel.spin_day_max_w.setValue(250.0)
        panel.spin_day_max_delta.setValue(8.0)
        panel._apply_assembly_ui_values(asm)

        _assert(abs(float(asm.LeftSideWidth) - 5.0) < 1.0e-6, "Displayed 5 m left width should save as 5 meter-native units")
        _assert(abs(float(asm.RightSideWidth) - 6.0) < 1.0e-6, "Displayed 6 m right width should save as 6 meter-native units")
        _assert(abs(float(asm.DaylightSearchStep) - 2.0) < 1.0e-6, "Displayed 2 m search step should save as 2 meter-native units")
        _assert(abs(float(asm.DaylightMaxSearchWidth) - 250.0) < 1.0e-6, "Displayed 250 m max width should save as 250 meter-native units")
        _assert(abs(float(asm.DaylightMaxWidthDelta) - 8.0) < 1.0e-6, "Displayed 8 m max delta should save as 8 meter-native units")
        _assert(panel._station_text_to_meters("5, 25, 37.5") == "5.000000, 25.000000, 37.500000", "Manual station text conversion should store meter-native values")

        print("[PASS] Section generator unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
