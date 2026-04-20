# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileNotice: Part of the Corridor Road addon.

"""
PVI editor unit-policy smoke test.

Run in FreeCAD Python environment:
    FreeCADCmd tests/regression/smoke_pvi_unit_policy.py
"""

import FreeCAD as App

from freecad.Corridor_Road.objects.obj_profile_bundle import ProfileBundle
from freecad.Corridor_Road.objects import unit_policy as _units
from freecad.Corridor_Road.objects.obj_project import ensure_project_properties
from freecad.Corridor_Road.objects.obj_stationing import Stationing
from freecad.Corridor_Road.qt_compat import QtWidgets
from freecad.Corridor_Road.ui.task_pvi_editor import PviEditorTaskPanel


def _assert(cond, msg):
    if not cond:
        raise Exception(msg)


def run():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    doc = App.newDocument("CRPviUnitPolicy")
    try:
        prj = doc.addObject("App::FeaturePython", "CorridorRoadProject")
        ensure_project_properties(prj)
        prj.LinearUnitDisplay = "mm"

        st = doc.addObject("Part::FeaturePython", "Stationing")
        Stationing(st)
        st.StationValues = [0.0, 50.0, 100.0, 150.0, 200.0]

        bundle = doc.addObject("Part::FeaturePython", "ProfileBundle")
        ProfileBundle(bundle)
        bundle.Stations = [_units.internal_length_from_meters(doc, float(s)) for s in st.StationValues]
        bundle.ElevEG = [_units.internal_length_from_meters(doc, float(z)) for z in [100.0, 102.0, 104.0, 106.0, 108.0]]
        bundle.ElevFG = [0.0, 0.0, 0.0, 0.0, 0.0]

        panel = PviEditorTaskPanel()
        rows = panel._read_pvi()
        _assert(panel.table.horizontalHeaderItem(0).text().endswith("(mm)"), "PVI station header should show millimeter unit")
        _assert(len(rows) == 3, "Starter PVI should still create three rows")
        _assert(abs(rows[0][0] - 0.0) < 1e-6 and abs(rows[2][0] - 200000.0) < 1e-6, "PVI stations should display in millimeters")
        _assert(abs(rows[1][1] - 104000.0) < 1e-6, "PVI elevations should display in millimeters")
        _assert(abs(rows[1][2] - 20000.0) < 1e-6, "Starter curve length should display as 20000 mm")
        starter_summary = panel._starter_load_summary_text(3, "ProfileBundle EG")
        _assert("Display unit: mm" in starter_summary, "Starter PVI summary should report display unit")
        _assert("Seed source: ProfileBundle EG" in starter_summary, "Starter PVI summary should report seed source")
        summary = str(panel.lbl_pvi_summary.text() or "")
        _assert("Grade 1: 0.000 -> 100000.000 mm" in summary, "PVI summary should display grade station range in millimeters")
        _assert("PVI @100000.000 mm: L=20000.000 mm" in summary, "PVI summary should display curve preview lengths in millimeters")

        panel.spin_min_tan.setValue(30000.0)
        panel._save_vertical_alignment()
        va = next(o for o in doc.Objects if str(getattr(getattr(o, "Proxy", None), "Type", "") or "") == "VerticalAlignment")
        _assert(abs(float(getattr(va, "MinTangent", 0.0)) - 30.0) < 1e-6, "Displayed 30000 mm min tangent should save as 30 meter-native units")
        fg_summary = panel._fg_generation_summary_text(5)
        _assert("Display unit: mm" in fg_summary, "FG generation summary should report display unit")
        _assert("Stations updated: 5" in fg_summary, "FG generation summary should report updated station count")

        print("[PASS] PVI editor unit-policy smoke test completed.")
    finally:
        App.closeDocument(doc.Name)


if __name__ == "__main__":
    run()
