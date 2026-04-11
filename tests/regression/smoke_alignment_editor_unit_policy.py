# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
Alignment editor unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_alignment_editor_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_alignment import HorizontalAlignment, ensure_alignment_properties
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_alignment_editor import AlignmentEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRAlignmentUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "m"

        aln = doc.addObject("Part::FeaturePython", "HorizontalAlignment")
        HorizontalAlignment(aln)
        ensure_alignment_properties(aln)
        aln.IPPoints = [
            App.Vector(0.0, 0.0, 0.0),
            App.Vector(30.0, 0.0, 0.0),
            App.Vector(60.0, 30.0, 0.0),
        ]
        aln.CurveRadii = [0.0, 120.0, 0.0]
        aln.TransitionLengths = [0.0, 15.0, 0.0]
        aln.MinRadius = 50.0
        aln.MinTangentLength = 20.0
        aln.MinTransitionLength = 10.0
        aln.TotalLength = 60.0

        panel = AlignmentEditorTaskPanel()

        _assert(panel.table.horizontalHeaderItem(2).text().endswith("(m)"), "Alignment radius column should show meter display unit")
        _assert(abs(float(panel._get_float(1, 2)) - 120.0) < 1.0e-6, "Curve radius should display as meters")
        _assert(abs(float(panel._get_float(1, 3)) - 15.0) < 1.0e-6, "Transition length should display as meters")
        _assert(abs(float(panel.spin_min_r.value()) - 50.0) < 1.0e-6, "Min radius should display as meters")
        _assert(abs(float(panel.spin_min_tan.value()) - 20.0) < 1.0e-6, "Min tangent should display as meters")
        _assert(abs(float(panel.spin_min_ls.value()) - 10.0) < 1.0e-6, "Min transition should display as meters")
        _assert("Display unit: m" in str(panel.lbl_info.text() or ""), "Alignment editor info should report display unit")
        _assert("Display unit: m" in panel.txt_report.toPlainText(), "Alignment editor report should report display unit")
        _assert("Total length: 60.000 m" in panel.txt_report.toPlainText(), "Report should format total length in meters")

        inspect_summary = panel._csv_inspect_summary_text(
            {
                "row_count": 3,
                "delimiter": ",",
                "encoding": "utf-8-sig",
                "header_guess": True,
                "linear_unit": "mm",
                "sample_rows": [[1, 2, 3, 4]],
            }
        )
        _assert("Display unit: m" in inspect_summary, "CSV inspect summary should report active display unit")
        _assert("CSV linear values: mm" in inspect_summary, "CSV inspect summary should report CSV linear unit")

        load_summary = panel._csv_load_summary_text(
            {
                "loaded": 2,
                "skipped": 1,
                "delimiter": ",",
                "encoding": "utf-8-sig",
                "header": True,
                "linear_unit": "mm",
                "skip_reasons": ["row 4: duplicate"],
            }
        )
        _assert("Display unit: m" in load_summary, "CSV load summary should report active display unit")
        _assert("CSV linear values: mm" in load_summary, "CSV load summary should report CSV linear unit")

        save_summary = panel._csv_save_summary_text(
            {
                "written": 2,
                "delimiter": ",",
                "encoding": "utf-8-sig",
                "header": True,
                "linear_unit": "m",
                "path": "alignment.csv",
            },
            "alignment.csv",
        )
        _assert("Display unit: m" in save_summary, "CSV save summary should report active display unit")
        _assert("CSV linear values: m" in save_summary, "CSV save summary should report CSV linear unit")

        panel._set_float(1, 2, 80.0)
        panel._set_float(1, 3, 12.0)
        panel.spin_min_tan.setValue(30.0)
        panel.spin_min_ls.setValue(18.0)
        panel._save_to_doc()

        _assert(abs(float(aln.CurveRadii[1]) - 80.0) < 1.0e-6, "Displayed 80 m radius should save as 80 meter-native units")
        _assert(abs(float(aln.TransitionLengths[1]) - 12.0) < 1.0e-6, "Displayed 12 m transition should save as 12 meter-native units")
        _assert(abs(float(aln.MinTangentLength) - 30.0) < 1.0e-6, "Displayed 30 m min tangent should save as 30 meter-native units")
        _assert(abs(float(aln.MinTransitionLength) - 18.0) < 1.0e-6, "Displayed 18 m min transition should save as 18 meter-native units")

        print("[PASS] Alignment editor unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
